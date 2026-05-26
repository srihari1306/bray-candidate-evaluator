"""
SharePoint integration service using Microsoft Graph API.
Fetches resumes from SharePoint Online document libraries.
"""

import asyncio
import os
import uuid
from typing import Optional
from pathlib import Path

import httpx

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.retry import retry_async

logger = get_logger("sharepoint")

# Supported resume file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}


class SharePointFile:
    """Represents a file from SharePoint."""

    def __init__(
        self,
        file_id: str,
        name: str,
        download_url: str,
        size: int,
        mime_type: str,
        web_url: str = "",
    ):
        self.file_id = file_id
        self.name = name
        self.download_url = download_url
        self.size = size
        self.mime_type = mime_type
        self.web_url = web_url

    @property
    def extension(self) -> str:
        return Path(self.name).suffix.lower()

    @property
    def is_supported(self) -> bool:
        return self.extension in SUPPORTED_EXTENSIONS


class SharePointService:
    """Service for interacting with SharePoint Online via Microsoft Graph API."""

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self.settings = get_settings()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    async def _get_access_token(self) -> str:
        """Acquire or refresh OAuth2 access token using client credentials."""
        import time

        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        token_url = f"https://login.microsoftonline.com/{self.settings.AZURE_TENANT_ID}/oauth2/v2.0/token"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.AZURE_CLIENT_ID,
                    "client_secret": self.settings.AZURE_CLIENT_SECRET,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            response.raise_for_status()
            data = response.json()

        self._access_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        logger.info("SharePoint access token acquired/refreshed")
        return self._access_token

    async def _graph_request(self, url: str, **kwargs) -> dict:
        """Make an authenticated request to Microsoft Graph API."""
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    async def list_resumes(self) -> list[SharePointFile]:
        """List all resume files in the configured SharePoint folder."""
        logger.info("Fetching resume list from SharePoint")

        drive_id = self.settings.SHAREPOINT_DRIVE_ID
        folder_path = self.settings.SHAREPOINT_FOLDER_PATH

        url = f"{self.GRAPH_BASE_URL}/drives/{drive_id}/root:/{folder_path}:/children"

        files: list[SharePointFile] = []
        next_link = url

        while next_link:
            data = await retry_async(
                self._graph_request,
                next_link,
                max_retries=3,
                operation_name="SharePoint list files",
            )

            for item in data.get("value", []):
                if "file" not in item:
                    continue  # Skip folders

                sp_file = SharePointFile(
                    file_id=item["id"],
                    name=item["name"],
                    download_url=item.get("@microsoft.graph.downloadUrl", ""),
                    size=item.get("size", 0),
                    mime_type=item.get("file", {}).get("mimeType", ""),
                    web_url=item.get("webUrl", ""),
                )

                if sp_file.is_supported:
                    files.append(sp_file)
                else:
                    logger.debug(f"Skipping unsupported file: {item['name']}")

            next_link = data.get("@odata.nextLink")

        logger.info(f"Found {len(files)} supported resume files in SharePoint")
        return files

    async def download_file(self, file: SharePointFile) -> bytes:
        """Download a file's content from SharePoint."""
        logger.info(f"Downloading: {file.name} ({file.size} bytes)")

        if not file.download_url:
            # Fetch download URL if not present
            drive_id = self.settings.SHAREPOINT_DRIVE_ID
            url = f"{self.GRAPH_BASE_URL}/drives/{drive_id}/items/{file.file_id}"
            data = await self._graph_request(url)
            file.download_url = data.get("@microsoft.graph.downloadUrl", "")

        async with httpx.AsyncClient() as client:
            response = await client.get(file.download_url, follow_redirects=True)
            response.raise_for_status()
            return response.content

    async def download_all_resumes(
        self, max_concurrent: int = 5
    ) -> list[tuple[SharePointFile, bytes]]:
        """Download all resumes with concurrency control."""
        files = await self.list_resumes()

        if not files:
            logger.warning("No resumes found in SharePoint")
            return []

        semaphore = asyncio.Semaphore(max_concurrent)
        results: list[tuple[SharePointFile, bytes]] = []

        async def download_with_semaphore(f: SharePointFile):
            async with semaphore:
                try:
                    content = await retry_async(
                        self.download_file,
                        f,
                        max_retries=2,
                        operation_name=f"Download {f.name}",
                    )
                    return (f, content)
                except Exception as e:
                    logger.error(f"Failed to download {f.name}: {e}")
                    return None

        tasks = [download_with_semaphore(f) for f in files]
        completed = await asyncio.gather(*tasks)
        results = [r for r in completed if r is not None]

        logger.info(f"Downloaded {len(results)}/{len(files)} resumes successfully")
        return results


# ─── Mock Implementation ────────────────────────────────────────────────────

class MockSharePointService(SharePointService):
    """Mock SharePoint service for local development."""

    MOCK_RESUMES = [
        {
            "id": "sp-1",
            "name": "John_Doe_Resume.pdf",
            "content": """
JOHN DOE
Email: john.doe@email.com | Phone: (555) 123-4567

PROFESSIONAL SUMMARY
Senior Cloud & AI Engineer with 8+ years of experience in building scalable cloud infrastructure
and cutting-edge AI systems. Expertise in Azure, Kubernetes, and agentic AI frameworks.

TECHNICAL SKILLS
- Cloud: Azure (AKS, Functions, DevOps), AWS (EC2, S3, Lambda), Terraform, Docker, Kubernetes
- AI/ML: LangChain, LangGraph, RAG Pipelines, GPT-4, Azure OpenAI, CrewAI, AutoGen
- Languages: Python, TypeScript, Go, Bash
- DevOps: CI/CD (GitHub Actions, Azure DevOps), Helm, ArgoCD
- Linux: Ubuntu Server, Bash Scripting, SSH, System Administration
- Databases: PostgreSQL, MongoDB, Redis, Elasticsearch

WORK EXPERIENCE
Senior AI Engineer | TechCorp Inc. | 2021 - Present
- Architected multi-agent AI orchestration system using LangGraph and CrewAI
- Built Azure Kubernetes infrastructure serving 50M+ requests/day
- Implemented Terraform IaC for 200+ cloud resources across 3 environments
- Designed RAG pipeline processing 100K+ documents with semantic search

Cloud Engineer | CloudSys Solutions | 2018 - 2021
- Managed Kubernetes clusters on Azure AKS with 99.99% uptime
- Built CI/CD pipelines using Azure DevOps and GitHub Actions
- Implemented Docker containerization for 30+ microservices
- Linux server administration and Bash automation scripts

PROJECTS
- AI Resume Analyzer: Built semantic resume matching system using embeddings and vector search
- Cloud Migration Platform: Led migration of 50+ legacy apps to Azure Kubernetes
- DevOps Automation: Created Terraform modules for multi-region Azure deployment

EDUCATION
M.S. Computer Science - Stanford University (2018)
B.S. Computer Science - UC Berkeley (2016)

CERTIFICATIONS
- Azure Solutions Architect Expert
- Kubernetes Administrator (CKA)
- AWS Solutions Architect Associate
            """,
        },
        {
            "id": "sp-2",
            "name": "Jane_Smith_Resume.pdf",
            "content": """
JANE SMITH
Email: jane.smith@email.com | Phone: (555) 987-6543

PROFESSIONAL SUMMARY
AI/ML Engineer with 6 years of experience in machine learning, NLP, and emerging agentic AI systems.
Passionate about building intelligent automation with modern AI frameworks.

TECHNICAL SKILLS
- AI/ML: PyTorch, TensorFlow, Hugging Face, LangChain, AutoGen, RAG Systems
- Cloud: AWS (SageMaker, EC2, S3), Azure (OpenAI, Cognitive Services), Docker
- Languages: Python, JavaScript, SQL
- Tools: Jupyter, MLflow, Weights & Biases, Git
- NLP: Transformers, BERT, GPT models, Semantic Search, Embeddings

WORK EXPERIENCE
AI Engineer | InnovateTech | 2022 - Present
- Built LangChain-based agentic workflows for automated customer support
- Implemented RAG pipelines with Azure AI Search and OpenAI embeddings
- Created multi-agent systems for document processing using AutoGen
- Fine-tuned transformer models for domain-specific NLP tasks

ML Engineer | DataDriven Co. | 2020 - 2022
- Developed production ML models for prediction and classification
- Built end-to-end ML pipelines with MLflow and Docker
- Implemented NLP solutions for text classification and entity extraction

Junior Developer | WebStart Inc. | 2018 - 2020
- Full-stack development with React and Node.js
- REST API development and database design
- Basic AWS cloud deployment

PROJECTS
- Multi-Agent Research Assistant: Built AI system with 5 specialized agents using CrewAI
- Semantic Search Engine: Created vector search system using FAISS and OpenAI embeddings
- Chatbot Platform: Developed enterprise chatbot with RAG and function calling

EDUCATION
M.S. Artificial Intelligence - Carnegie Mellon University (2020)
B.S. Computer Science - MIT (2018)

CERTIFICATIONS
- AWS Machine Learning Specialty
- DeepLearning.AI LangChain Certificate
            """,
        },
        {
            "id": "sp-3",
            "name": "Alex_Chen_Resume.pdf",
            "content": """
ALEX CHEN
Email: alex.chen@email.com | Phone: (555) 456-7890

PROFESSIONAL SUMMARY
Full-Stack Developer with 5 years of experience in web development and growing interest in
cloud technologies. Currently transitioning into cloud engineering roles.

TECHNICAL SKILLS
- Frontend: React, TypeScript, Next.js, Vue.js, HTML/CSS, Tailwind
- Backend: Node.js, Express, Python, FastAPI, Django
- Databases: PostgreSQL, MongoDB, Redis
- Cloud: Basic AWS (EC2, S3, RDS), Docker (basic)
- Tools: Git, VS Code, Jira, Confluence
- Testing: Jest, Pytest, Cypress

WORK EXPERIENCE
Senior Full-Stack Developer | WebDev Pro | 2022 - Present
- Built responsive web applications using React and TypeScript
- Developed REST APIs with Node.js and FastAPI
- Deployed applications on AWS EC2 with basic Docker setup
- Implemented authentication systems with OAuth2

Full-Stack Developer | AppFactory | 2020 - 2022
- Created customer-facing web portals with Vue.js
- Built backend services with Django and PostgreSQL
- Basic Git workflow and CI setup

Junior Developer | StartupXYZ | 2019 - 2020
- Frontend development with React
- Bug fixes and feature development

PROJECTS
- E-Commerce Platform: Full-stack Next.js application with Stripe payments
- Task Management App: React + Node.js project management tool
- Personal Blog: Static site with Gatsby and GraphQL

EDUCATION
B.S. Computer Science - University of Washington (2019)

CERTIFICATIONS
- AWS Cloud Practitioner
            """,
        },
        {
            "id": "sp-4",
            "name": "Sarah_Johnson_Resume.pdf",
            "content": """
SARAH JOHNSON
Email: sarah.j@email.com | Phone: (555) 321-0987

PROFESSIONAL SUMMARY
DevOps & Platform Engineer with 7 years of experience in cloud infrastructure, automation,
and building developer platforms. Expert in Kubernetes, Linux, and infrastructure as code.

TECHNICAL SKILLS
- Cloud: Azure (AKS, DevOps, Functions, Storage), AWS (EKS, EC2, Lambda), GCP (GKE)
- Containers: Kubernetes, Docker, Helm, Istio Service Mesh
- IaC: Terraform, Pulumi, CloudFormation, Ansible
- CI/CD: Azure DevOps, GitHub Actions, Jenkins, ArgoCD, Flux
- Linux: Ubuntu, CentOS, RHEL, Bash/Zsh scripting, systemd, cron
- Monitoring: Prometheus, Grafana, Azure Monitor, Datadog
- Networking: VPN, Load Balancers, DNS, Firewalls, TCP/IP
- Languages: Bash, Python, Go, YAML/HCL

WORK EXPERIENCE
Senior Platform Engineer | InfraScale | 2021 - Present
- Designed and managed 15+ Kubernetes clusters across Azure and AWS
- Built Terraform modules library used by 200+ engineers
- Implemented GitOps workflow with ArgoCD and Flux
- Created custom Kubernetes operators in Go
- Linux server hardening and security compliance automation
- Built comprehensive monitoring with Prometheus and Grafana

DevOps Engineer | CloudOps Inc. | 2019 - 2021
- Managed CI/CD pipelines for 50+ microservices
- Docker containerization and Kubernetes deployment automation
- Bash scripting for infrastructure automation
- SSH key management and access control
- Linux server administration across 100+ servers

Systems Administrator | DataCenter Ltd. | 2017 - 2019
- Linux server administration (Ubuntu, CentOS)
- Bash scripting for backup and monitoring automation
- Docker adoption and container migration
- Network configuration and troubleshooting

PROJECTS
- K8s Platform: Self-service Kubernetes platform with custom CLI and web dashboard
- Terraform Registry: Internal module registry with 50+ reusable modules
- Incident Response Bot: Automated incident detection and escalation system

EDUCATION
B.S. Computer Engineering - Georgia Tech (2017)

CERTIFICATIONS
- Certified Kubernetes Administrator (CKA)
- Certified Kubernetes Security Specialist (CKS)
- Azure DevOps Engineer Expert
- HashiCorp Terraform Associate
- Red Hat Certified System Administrator (RHCSA)
            """,
        },
        {
            "id": "sp-5",
            "name": "Michael_Brown_Resume.pdf",
            "content": """
MICHAEL BROWN
Email: m.brown@email.com | Phone: (555) 654-3210

PROFESSIONAL SUMMARY
Data Scientist transitioning to AI Engineering with 4 years of experience in
machine learning, data analysis, and recently exploring LLM applications.

TECHNICAL SKILLS
- ML/AI: Scikit-learn, XGBoost, TensorFlow, Basic LangChain
- Data: Pandas, NumPy, SQL, Spark, Tableau, Power BI
- Cloud: Basic Azure (ML Studio), AWS SageMaker
- Languages: Python, R, SQL
- Tools: Jupyter, Git, Docker (basic)

WORK EXPERIENCE
Data Scientist | AnalyticsPro | 2022 - Present
- Built predictive models for customer churn and revenue forecasting
- Created dashboards with Tableau and Power BI
- Basic exploration of LLM APIs (OpenAI) for text analysis
- Implemented basic RAG prototype for internal knowledge base

Junior Data Scientist | DataInsights | 2020 - 2022
- Statistical analysis and A/B testing
- ML model development with Scikit-learn
- Data pipeline development with SQL and Python
- Basic cloud deployment on AWS

PROJECTS
- Customer Segmentation: K-means clustering with visualization dashboard
- Sentiment Analyzer: NLP model for product review analysis
- Sales Forecaster: Time series prediction with Prophet

EDUCATION
M.S. Data Science - Columbia University (2020)
B.S. Statistics - UCLA (2018)

CERTIFICATIONS
- Google Data Analytics Professional Certificate
- IBM Data Science Professional Certificate
            """,
        },
    ]

    async def list_resumes(self) -> list[SharePointFile]:
        """Return mock resume files."""
        logger.info("[MOCK] Listing resumes from mock data")
        return [
            SharePointFile(
                file_id=r["id"],
                name=r["name"],
                download_url=f"mock://resumes/{r['id']}",
                size=len(r["content"].encode()),
                mime_type="application/pdf",
                web_url=f"https://sharepoint.example.com/resumes/{r['name']}",
            )
            for r in self.MOCK_RESUMES
        ]

    async def download_file(self, file: SharePointFile) -> bytes:
        """Return mock resume content."""
        for r in self.MOCK_RESUMES:
            if r["id"] == file.file_id:
                return r["content"].encode()
        raise FileNotFoundError(f"Mock resume not found: {file.file_id}")

    def get_mock_text(self, file_id: str) -> str:
        """Get pre-parsed text for a mock resume (bypasses Doc Intelligence)."""
        for r in self.MOCK_RESUMES:
            if r["id"] == file_id:
                return r["content"]
        return ""


class LocalFileSystemService(SharePointService):
    """Service that reads resumes from a local directory instead of SharePoint."""

    def __init__(self):
        super().__init__()
        # Path to local resumes folder in backend directory
        self.local_dir = Path(os.getcwd()) / "resumes"
        self.local_dir.mkdir(exist_ok=True)

    async def list_resumes(self) -> list[SharePointFile]:
        logger.info(f"Fetching resumes from local directory: {self.local_dir}")
        files = []
        for file_path in self.local_dir.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(SharePointFile(
                    file_id=file_path.name,
                    name=file_path.name,
                    download_url=f"local://{file_path.name}",
                    size=file_path.stat().st_size,
                    mime_type="application/pdf",
                    web_url=f"file://{file_path.absolute()}"
                ))
        return files

    async def download_file(self, file: SharePointFile) -> bytes:
        logger.info(f"Reading local file: {file.name}")
        file_path = self.local_dir / file.name
        with open(file_path, "rb") as f:
            return f.read()


def get_sharepoint_service() -> SharePointService:
    """Factory for SharePoint service based on mock mode and config."""
    settings = get_settings()
    if settings.MOCK_MODE:
        return MockSharePointService()
        
    # If no valid Azure AD Client ID is provided, automatically fallback to local files
    if not settings.AZURE_CLIENT_ID or settings.AZURE_CLIENT_ID == "your-client-id":
        logger.warning("No Azure AD Client ID found. Falling back to Local File System instead of SharePoint.")
        return LocalFileSystemService()
        
    return SharePointService()
