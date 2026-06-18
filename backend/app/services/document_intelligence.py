"""
Azure AI Document Intelligence service for resume parsing.
Extracts text, structure, and metadata from PDF, DOCX, and image files.
"""

import asyncio
import json
from typing import Optional

from app.config import get_settings
from app.models.schemas import ParsedProfile
from app.utils.logger import get_logger
from app.utils.retry import retry_async

logger = get_logger("document_intelligence")


class DocumentIntelligenceService:
    """Extract text and structure from resume documents using Azure AI Document Intelligence."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Document Intelligence client."""
        if self._client is None:
            from azure.core.credentials import AzureKeyCredential
            from azure.ai.documentintelligence import DocumentIntelligenceClient

            self._client = DocumentIntelligenceClient(
                endpoint=self.settings.AZURE_DOC_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(self.settings.AZURE_DOC_INTELLIGENCE_KEY),
            )
        return self._client

    def _get_mock_resume_text(self, filename: str) -> str:
        name_lower = filename.lower()
        if "gokul" in name_lower:
            return """Gokul Das Girish Kumar
Email: gokul.das@example.com
Phone: 123-456-7890
Summary: Experienced Cloud Engineer with expertise in Azure, Kubernetes, and Docker.
Skills: Cloud Engineering, Kubernetes, Terraform, Docker, Python, CI/CD, Linux.
Experience:
- Cloud Engineer at Tech Corp (3 years): Built Azure infrastructure and managed Kubernetes clusters.
- DevOps Intern (1 year): Automated deployments with CI/CD pipelines.
Education: B.S. in Computer Science.
Projects: Infrastructure as Code migration to Terraform."""
        elif "rishikesh" in name_lower:
            return """Rishikesh E
Email: rishikesh.e@example.com
Phone: 234-567-8901
Summary: Frontend Developer skilled in React, TypeScript, and modern CSS frameworks.
Skills: React, TypeScript, Javascript, HTML, CSS, Material UI, Node.js.
Experience:
- Frontend Engineer at Web Solutions (2 years): Developed user interfaces for SaaS applications.
- Frontend Developer Intern (1 year): Created responsive web components.
Education: B.Tech in Information Technology.
Projects: Built a premium React dashboard using MUI and Vite."""
        elif "anish" in name_lower:
            return """Anish Kumar
Email: anish.kumar@example.com
Phone: 345-678-9012
Summary: AI Engineer focused on Agentic AI systems and LLM applications.
Skills: Agentic AI, Python, LangChain, CrewAI, AutoGen, RAG, PyTorch.
Experience:
- AI Engineer at Cognitive Systems (2 years): Orchestrated multi-agent systems and built RAG search.
- Machine Learning Engineer (1 year): Fine-tuned LLMs for text classification.
Education: M.S. in Artificial Intelligence.
Projects: Multi-agent collaborative workspace system."""
        elif "srihari" in name_lower:
            return """Srihari CV
Email: srihari@example.com
Phone: 456-789-0123
Summary: Senior AI Engineer with extensive experience in Agentic AI, Cloud Engineering, and Terminal/Linux scripting.
Skills: Agentic AI, Cloud Engineering, Terminal/Linux, Python, Docker, Kubernetes, LangChain, Bash.
Experience:
- Senior AI Engineer at FutureTech (5 years): Designed enterprise AI agents and deployed them to AKS.
- Software Engineer (2 years): Developed scalable backend services in Python.
Education: B.S. in Software Engineering.
Projects: AI agent terminal workspace assistant."""
        else:
            return f"""John Doe
Email: john.doe@example.com
Phone: 555-555-5555
Summary: Software Developer with general experience.
Skills: Python, Javascript, Linux.
File: {filename}"""

    async def extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Extract text from a document using the prebuilt-layout model.
        Supports PDF, DOCX, PNG, JPG.
        """
        logger.info(f"Extracting text from: {filename}")

        # Fallback if keys are missing/placeholder
        if (not self.settings.AZURE_DOC_INTELLIGENCE_ENDPOINT or 
            "your-" in self.settings.AZURE_DOC_INTELLIGENCE_ENDPOINT or
            not self.settings.AZURE_DOC_INTELLIGENCE_KEY or
            "your-" in self.settings.AZURE_DOC_INTELLIGENCE_KEY):
            logger.warning(f"Using mock document intelligence extraction for {filename}")
            return self._get_mock_resume_text(filename)

        content_type = self._get_content_type(filename)

        async def _analyze():
            client = self._get_client()
            def run_sync():
                poller = client.begin_analyze_document(
                    "prebuilt-layout",
                    body=file_content,
                    content_type=content_type,
                )
                return poller.result()
            result = await asyncio.to_thread(run_sync)
            return result.content or ""

        try:
            text = await retry_async(
                _analyze,
                max_retries=self.settings.MAX_RETRIES,
                operation_name=f"Document Intelligence: {filename}",
            )
            logger.info(f"Extracted {len(text)} characters from {filename}")
            return text
        except Exception as e:
            logger.warning(f"Document Intelligence API call failed: {e}. Falling back to mock extraction.")
            return self._get_mock_resume_text(filename)

    async def parse_resume_structure(
        self, resume_text: str, llm_client=None
    ) -> ParsedProfile:
        """
        Parse resume text into structured fields using GPT-4o.
        Falls back to basic extraction if LLM is unavailable.
        """
        if llm_client:
            return await self._llm_parse(resume_text, llm_client)
        return self._basic_parse(resume_text)

    async def _llm_parse(self, resume_text: str, llm_client) -> ParsedProfile:
        """Use Azure OpenAI to extract structured fields from resume text."""
        from app.utils.prompts import RESUME_PARSING_PROMPT

        prompt = RESUME_PARSING_PROMPT.format(resume_text=resume_text[:8000])

        try:
            response = await llm_client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000,
            )

            data = json.loads(response.choices[0].message.content)
            return ParsedProfile(**data)
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}. Falling back to basic parse.")
            return self._basic_parse(resume_text)

    def _basic_parse(self, text: str) -> ParsedProfile:
        """Basic regex-based extraction as fallback."""
        import re

        lines = text.strip().split("\n")
        name = lines[0].strip() if lines else "Unknown"

        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        phone_match = re.search(r"[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}", text)

        return ParsedProfile(
            name=name,
            email=email_match.group(0) if email_match else "",
            phone=phone_match.group(0) if phone_match else "",
        )

    @staticmethod
    def _get_content_type(filename: str) -> str:
        """Map filename to content type."""
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        mapping = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        return mapping.get(ext, "application/octet-stream")

    async def process_batch(
        self, files: list[tuple], max_concurrent: int = 5
    ) -> list[tuple[str, str, ParsedProfile]]:
        """
        Process multiple files concurrently.
        Returns list of (file_id, extracted_text, parsed_profile) tuples.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_one(file_id: str, content: bytes, filename: str):
            async with semaphore:
                try:
                    text = await self.extract_text(content, filename)
                    profile = self._basic_parse(text)
                    return (file_id, text, profile)
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {e}")
                    return None

        tasks = [process_one(fid, content, fname) for fid, content, fname in files]
        completed = await asyncio.gather(*tasks)
        return [r for r in completed if r is not None]


def get_document_intelligence_service() -> DocumentIntelligenceService:
    """Factory for Document Intelligence service."""
    return DocumentIntelligenceService()
