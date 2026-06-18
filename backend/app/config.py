"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── Application ───
    APP_NAME: str = "Candidate Evaluator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5174,http://localhost:5173,http://localhost:3000,http://localhost:3001"

    # ─── Azure AD / Entra ID ───
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_AD_AUDIENCE: str = ""

    # ─── Azure OpenAI ───
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 3072

    # ─── Azure AI Search ───
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_API_KEY: str = ""
    AZURE_SEARCH_INDEX_NAME: str = "resume-index"

    # ─── Azure AI Document Intelligence ───
    AZURE_DOC_INTELLIGENCE_ENDPOINT: str = ""
    AZURE_DOC_INTELLIGENCE_KEY: str = ""

    # ─── Azure Computer Vision ───
    AZURE_COMPUTER_VISION_ENDPOINT: str = ""
    AZURE_COMPUTER_VISION_KEY: str = ""

    # ─── Azure Blob Storage ───
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "resumes"

    # ─── Azure Key Vault ───
    AZURE_KEYVAULT_URL: str = ""

    # ─── Azure Monitor / App Insights ───
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = ""

    # ─── SharePoint ───
    SHAREPOINT_SITE_URL: str = ""
    SHAREPOINT_SITE_ID: str = ""
    SHAREPOINT_DRIVE_ID: str = ""
    SHAREPOINT_FOLDER_PATH: str = "Resumes"

    # ─── Processing ───
    CHUNK_SIZE_TOKENS: int = 800
    CHUNK_OVERLAP_TOKENS: int = 100
    MAX_CONCURRENT_PROCESSING: int = 5
    EMBEDDING_BATCH_SIZE: int = 16
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 1.0

    # ─── Scoring Weights ───
    SCORE_WEIGHT_JD_MATCH: float = 0.5
    SCORE_WEIGHT_SKILLS: float = 0.3
    SCORE_WEIGHT_EXPERIENCE: float = 0.2

    # ─── Smart Interviewer: Gmail SMTP Email ───
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    MOCK_EMAIL: bool = False

    # ─── Smart Interviewer: Persistence ───
    INTERVIEWS_JSON_PATH: str = "data/interviews.json"

    # ─── Smart Interviewer: Azure Speech Service ───
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "eastus"

    # ─── Smart Interviewer: Teams Meeting ───
    TEAMS_STATIC_MEETING_URL: str = ""
    INTERVIEW_PANEL_BASE_URL: str = "http://localhost:3001"

    # ─── Smart Interviewer: Blob Recordings ───
    AZURE_BLOB_RECORDINGS_CONTAINER: str = "interview-recordings"

    # ─── Smart Interviewer: Interview Config ───
    INTERVIEW_QUESTIONS: str = '["Tell me about yourself.","Describe a challenging project you worked on.","Why are you interested in this role?"]'
    INTERVIEW_SESSION_SECRET: str = "change_this_to_a_long_random_secret"

    # ─── Smart Interviewer: Proctoring Config ───
    PROCTORING_FRAME_INTERVAL_SECONDS: int = 5
    PROCTORING_SUSPICIOUS_DOMAINS: str = "google.com,chatgpt.com,chat.openai.com,bing.com,stackoverflow.com,chegg.com"

    # ─── Azure Cosmos DB ───
    AZURE_COSMOS_ENDPOINT: str = ""
    AZURE_COSMOS_KEY: str = ""
    AZURE_COSMOS_DATABASE: str = "bray-evaluator"
    AZURE_COSMOS_SESSIONS_CONTAINER: str = "sessions"
    AZURE_COSMOS_EVALUATIONS_CONTAINER: str = "evaluations"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
