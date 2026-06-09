"""
Blob Recording Service — SAS URL generation for interview recording uploads.
Generates time-limited Shared Access Signature URLs for Azure Blob Storage.
"""

from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("services.blob_recording")


def _is_placeholder(conn_str: str) -> bool:
    if not conn_str:
        return True
    conn_str_lower = conn_str.lower()
    return "accountname=..." in conn_str_lower or "your-account" in conn_str_lower or "endpoint=" in conn_str_lower and "xxx" in conn_str_lower

def generate_upload_sas_url(session_id: str) -> dict:
    """
    Generate a write-only SAS URL for uploading an interview recording.

    Args:
        session_id: Interview session ID (used as blob name)

    Returns:
        { sas_url: str, blob_name: str }
    """
    settings = get_settings()
    blob_name = f"{session_id}.webm"
    container_name = settings.AZURE_BLOB_RECORDINGS_CONTAINER

    if _is_placeholder(settings.AZURE_STORAGE_CONNECTION_STRING):
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not configured or placeholder — returning mock URL")
        return {
            "sas_url": f"https://mock-storage.blob.core.windows.net/{container_name}/{blob_name}?mock=true",
            "blob_name": blob_name,
        }

    try:
        from azure.storage.blob import (
            BlobServiceClient,
            generate_blob_sas,
            BlobSasPermissions,
        )

        blob_service = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)

        # Ensure container exists
        container_client = blob_service.get_container_client(container_name)
        try:
            container_client.get_container_properties()
        except Exception:
            logger.info(f"Creating blob container: {container_name}")
            container_client.create_container()

        # Extract account name and key from connection string
        account_name = blob_service.account_name
        # Parse account key from connection string
        conn_parts = dict(
            part.split("=", 1)
            for part in settings.AZURE_STORAGE_CONNECTION_STRING.split(";")
            if "=" in part
        )
        account_key = conn_parts.get("AccountKey", "")

        # Generate SAS token (write-only, 30-minute expiry)
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

        sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

        logger.info(f"✓ Upload SAS URL generated for {blob_name} (30-min expiry)")
        return {"sas_url": sas_url, "blob_name": blob_name}

    except Exception as e:
        logger.error(f"✗ Failed to generate upload SAS URL: {e}", exc_info=True)
        raise


def generate_read_sas_url(blob_name: str) -> str:
    """
    Generate a time-limited read URL for recruiter playback.

    Args:
        blob_name: The blob name (e.g., "session_uuid.webm")

    Returns:
        SAS URL with read permission
    """
    settings = get_settings()
    container_name = settings.AZURE_BLOB_RECORDINGS_CONTAINER

    if _is_placeholder(settings.AZURE_STORAGE_CONNECTION_STRING):
        return f"https://mock-storage.blob.core.windows.net/{container_name}/{blob_name}?mock=true"

    try:
        from azure.storage.blob import (
            BlobServiceClient,
            generate_blob_sas,
            BlobSasPermissions,
        )

        blob_service = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        account_name = blob_service.account_name
        conn_parts = dict(
            part.split("=", 1)
            for part in settings.AZURE_STORAGE_CONNECTION_STRING.split(";")
            if "=" in part
        )
        account_key = conn_parts.get("AccountKey", "")

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=2),
        )

        return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

    except Exception as e:
        logger.error(f"✗ Failed to generate read SAS URL: {e}", exc_info=True)
        return ""
