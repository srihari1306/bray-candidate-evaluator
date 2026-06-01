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
                    web_url=f"http://localhost:8000/resumes/{file_path.name}"
                ))
        return files

    async def download_file(self, file: SharePointFile) -> bytes:
        logger.info(f"Reading local file: {file.name}")
        file_path = self.local_dir / file.name
        with open(file_path, "rb") as f:
            return f.read()


def get_sharepoint_service() -> SharePointService:
    """Factory for SharePoint service based on config."""
    settings = get_settings()
        
    # If no valid Azure AD Client ID is provided, automatically fallback to local files
    if not settings.AZURE_CLIENT_ID or settings.AZURE_CLIENT_ID == "your-client-id":
        logger.warning("No Azure AD Client ID found. Falling back to Local File System instead of SharePoint.")
        return LocalFileSystemService()
        
    return SharePointService()
