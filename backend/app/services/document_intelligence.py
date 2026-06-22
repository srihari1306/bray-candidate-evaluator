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


    async def extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Extract text from a document using the prebuilt-layout model.
        Supports PDF, DOCX, PNG, JPG.
        """
        logger.info(f"Extracting text from: {filename}")

        # Check if keys are missing/placeholder
        if (not self.settings.AZURE_DOC_INTELLIGENCE_ENDPOINT or 
            "your-" in self.settings.AZURE_DOC_INTELLIGENCE_ENDPOINT or
            not self.settings.AZURE_DOC_INTELLIGENCE_KEY or
            "your-" in self.settings.AZURE_DOC_INTELLIGENCE_KEY):
            raise ValueError("Azure AI Document Intelligence credentials are not properly configured.")

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

        text = await retry_async(
            _analyze,
            max_retries=self.settings.MAX_RETRIES,
            operation_name=f"Document Intelligence: {filename}",
        )
        logger.info(f"Extracted {len(text)} characters from {filename}")
        return text

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
