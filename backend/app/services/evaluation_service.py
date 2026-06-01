"""
AI Evaluation Engine using Azure OpenAI GPT-4o.
Evaluates candidates against job descriptions and custom skill categories.
"""

import json
import uuid
import base64
import asyncio
import time
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.models.schemas import (
    CandidateResult, SkillScore, ParsedProfile,
    RecommendationType, ConfidenceLevel,
    EvaluationRequest, EvaluationResponse,
    EvaluationStatus, EvaluationStatusResponse,
)
from app.services.sharepoint_service import get_sharepoint_service
from app.services.document_intelligence import get_document_intelligence_service
from app.services.chunking_service import get_chunking_service
from app.services.embedding_service import get_embedding_service
from app.services.search_service import get_search_service, SearchDocument
from app.utils.logger import get_logger
from app.utils.prompts import build_evaluation_prompt
from app.utils.retry import retry_async

logger = get_logger("evaluation")



class EvaluationEngine:
    """Core AI evaluation engine that orchestrates the full pipeline."""

    def __init__(self):
        self.settings = get_settings()
        self._llm_client = None

    @property
    def llm_client(self):
        if self._llm_client is None:
            from openai import AzureOpenAI
            self._llm_client = AzureOpenAI(
                api_key=self.settings.AZURE_OPENAI_API_KEY,
                api_version=self.settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            )
        return self._llm_client

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        """Execute the full evaluation pipeline."""
        evaluation_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        logger.info(f"Starting evaluation {evaluation_id}")

        try:
            # Step 1: Fetch resumes
            sp_service = get_sharepoint_service()
            resume_files = await sp_service.download_all_resumes(
                max_concurrent=self.settings.MAX_CONCURRENT_PROCESSING
            )

            if not resume_files:
                return EvaluationResponse(
                    evaluation_id=evaluation_id,
                    status=EvaluationStatus.COMPLETED,
                    job_title=request.job_title,
                )

            # Step 2: Parse resumes
            doc_service = get_document_intelligence_service()
            chunking_service = get_chunking_service()

            async def parse_resume(sp_file, content):
                try:
                    text = await doc_service.extract_text(content, sp_file.name)
                    profile = doc_service._basic_parse(text)
                    return {
                        "file_id": sp_file.file_id,
                        "filename": sp_file.name,
                        "text": text,
                        "profile": profile,
                        "web_url": sp_file.web_url,
                    }
                except Exception as e:
                    logger.error(f"Failed to parse {sp_file.name}: {e}")
                    return None

            parse_tasks = [parse_resume(sp_file, content) for sp_file, content in resume_files]
            parsed_results = await asyncio.gather(*parse_tasks)
            parsed_resumes = [res for res in parsed_results if res is not None]

            # Step 3: Chunk and embed
            embedding_service = get_embedding_service()
            all_chunks = []
            all_texts = []

            for resume in parsed_resumes:
                chunks = chunking_service.chunk_text(resume["text"], resume["profile"].name)
                for chunk in chunks:
                    all_chunks.append({"chunk": chunk, "resume": resume})
                    all_texts.append(chunk.text)

            embeddings = await embedding_service.generate_embeddings_batch(all_texts) if all_texts else []

            # Step 4: Index
            search_service = get_search_service()
            if request.reindex:
                await search_service.delete_all_documents()
            await search_service.create_or_update_index()

            search_docs = []
            for i, item in enumerate(all_chunks):
                chunk = item["chunk"]
                resume = item["resume"]
                profile = resume["profile"]
                raw_doc_id = f"{resume['file_id']}-{chunk.chunk_index}"
                safe_doc_id = base64.urlsafe_b64encode(raw_doc_id.encode('utf-8')).decode('ascii').rstrip("=")
                
                search_docs.append(SearchDocument(
                    doc_id=safe_doc_id,
                    candidate_name=profile.name,
                    resume_text=chunk.text,
                    skills=profile.skills,
                    projects=", ".join(profile.projects),
                    experience=", ".join(profile.work_history),
                    resume_link=resume.get("web_url", ""),
                    content_vector=embeddings[i] if i < len(embeddings) else [],
                    chunk_index=chunk.chunk_index,
                    total_chunks=chunk.total_chunks,
                    skill_tags=profile.technologies,
                ))
            await search_service.index_documents(search_docs)

            # Step 5: Evaluate candidates
            skills_input = [{"name": s.name, "weight": s.weight} for s in request.skills]
            candidate_texts = {}
            for resume in parsed_resumes:
                name = resume["profile"].name
                candidate_texts[name] = resume

            async def eval_candidate(name, cdata):
                return await self._evaluate_candidate(
                    candidate_name=name,
                    resume_text=cdata["text"],
                    profile=cdata["profile"],
                    filename=cdata["filename"],
                    web_url=cdata.get("web_url", ""),
                    file_id=cdata["file_id"],
                    job_description=request.job_description,
                    skills=skills_input,
                )

            eval_tasks = [eval_candidate(name, cdata) for name, cdata in candidate_texts.items()]
            eval_results = await asyncio.gather(*eval_tasks)
            candidates_results = [res for res in eval_results if res is not None]

            candidates_results.sort(key=lambda c: c.overall_score, reverse=True)
            elapsed = time.time() - start_time

            return EvaluationResponse(
                evaluation_id=evaluation_id,
                status=EvaluationStatus.COMPLETED,
                job_title=request.job_title,
                job_description_preview=request.job_description[:200] + "...",
                skills_evaluated=[s.name for s in request.skills],
                total_resumes_processed=len(parsed_resumes),
                candidates=candidates_results,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                processing_time_seconds=round(elapsed, 2),
            )
        except Exception as e:
            logger.error(f"Evaluation {evaluation_id} failed: {e}", exc_info=True)
            return EvaluationResponse(
                evaluation_id=evaluation_id,
                status=EvaluationStatus.FAILED,
                job_title=request.job_title,
            )

    async def _evaluate_candidate(
        self, candidate_name, resume_text, profile, filename,
        web_url, file_id, job_description, skills
    ) -> Optional[CandidateResult]:
        """Evaluate a single candidate."""
        logger.info(f"Evaluating candidate: {candidate_name}")

        # Production: use GPT-4o
        prompt = build_evaluation_prompt(job_description, resume_text, skills)
        async def _call():
            response = self.llm_client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are an expert technical recruiter."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2, max_tokens=3000,
            )
            return json.loads(response.choices[0].message.content)

        data = await retry_async(_call, max_retries=2, operation_name=f"Evaluate {candidate_name}")
        return self._build_result(data, candidate_name, profile, filename, web_url, file_id, skills)

    def _build_result(self, data, candidate_name, profile, filename, web_url, file_id, skills):
        skill_scores = [
            SkillScore(skill=ss["skill"], score=min(max(ss["score"], 0), 100),
                       confidence=ConfidenceLevel(ss.get("confidence", "Medium")),
                       evidence=ss.get("evidence", []))
            for ss in data.get("skill_scores", [])
        ]
        overall = min(max(data.get("overall_score", 50), 0), 100)
        rec = self._get_recommendation(overall)
        return CandidateResult(
            id=file_id, candidate_name=data.get("candidate_name", candidate_name),
            email=profile.email, overall_score=overall, overall_recommendation=rec,
            skill_scores=skill_scores,
            missing_skills=data.get("missing_skills", []),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            summary=data.get("summary", ""),
            recommendation=data.get("recommendation", ""),
            interview_questions=data.get("interview_questions", []),
            resume_url=web_url, resume_filename=filename, parsed_profile=profile,
        )

    @staticmethod
    def _get_recommendation(score: int) -> RecommendationType:
        if score >= 85: return RecommendationType.STRONG_MATCH
        if score >= 70: return RecommendationType.GOOD_MATCH
        if score >= 55: return RecommendationType.MODERATE_MATCH
        if score >= 40: return RecommendationType.WEAK_MATCH
        return RecommendationType.NOT_RECOMMENDED


def get_evaluation_engine() -> EvaluationEngine:
    return EvaluationEngine()
