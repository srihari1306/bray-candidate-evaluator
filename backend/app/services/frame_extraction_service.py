"""
Frame Extraction Service — downloads recordings and extracts frames via OpenCV.
"""

import asyncio
import os
import tempfile
import cv2

import httpx

from app.config import get_settings
from app.services.blob_recording_service import generate_read_sas_url
from app.utils.logger import get_logger

logger = get_logger("services.frame_extraction")


async def download_blob(sas_url: str) -> bytes:
    """
    Download a blob from Azure Blob Storage using a SAS URL.
    Returns raw bytes.
    """
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(sas_url)
        response.raise_for_status()
        return response.content


async def extract_frames(blob_name: str, interval_seconds: int = 5) -> list[bytes]:
    """
    Extract frames from a recording blob at the specified interval.

    1. Generates a fresh read SAS URL for the blob.
    2. Downloads the blob.
    3. Writes to a temp file and runs OpenCV to extract JPEG frames.
    4. Returns a list of JPEG byte arrays.

    Args:
        blob_name: The blob name (e.g., "session_uuid_camera.webm")
        interval_seconds: Seconds between extracted frames.

    Returns:
        List of JPEG byte arrays, one per extracted frame.
    """
    if not blob_name:
        logger.warning("Empty blob_name — skipping frame extraction")
        return []

    # Generate fresh SAS URL
    sas_url = generate_read_sas_url(blob_name)

    if not sas_url:
        logger.warning(f"Could not generate SAS URL for {blob_name}")
        return []



    # Download blob bytes
    try:
        logger.info(f"Downloading recording blob: {blob_name}")
        video_bytes = await download_blob(sas_url)
        logger.info(f"Downloaded {len(video_bytes)} bytes for {blob_name}")
    except Exception as e:
        logger.error(f"Failed to download blob {blob_name}: {e}", exc_info=True)
        return []

    # Run OpenCV extraction in a background thread to prevent blocking the event loop
    frames = await asyncio.to_thread(_extract_frames_cv2, video_bytes, interval_seconds, blob_name)
    return frames

def _extract_frames_cv2(video_bytes: bytes, interval_seconds: int, blob_name: str) -> list[bytes]:
    """Synchronous function to extract frames using OpenCV."""
    frames = []
    temp_file_path = ""
    try:
        # Write video bytes to a temporary file
        fd, temp_file_path = tempfile.mkstemp(suffix=".webm")
        with os.fdopen(fd, 'wb') as f:
            f.write(video_bytes)

        cap = cv2.VideoCapture(temp_file_path)
        if not cap.isOpened():
            logger.error(f"OpenCV failed to open video file for {blob_name}")
            return frames

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or not fps:
            fps = 30.0  # Fallback assumption if metadata is missing

        frame_interval = max(1, int(fps * interval_seconds))
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                success, buffer = cv2.imencode('.jpg', frame)
                if success:
                    frames.append(buffer.tobytes())
            frame_count += 1

        cap.release()
        logger.info(f"Extracted {len(frames)} frames from {blob_name}")
        
    except Exception as e:
        logger.error(f"OpenCV execution error for {blob_name}: {e}", exc_info=True)
    finally:
        # Cleanup temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp file {temp_file_path}: {cleanup_err}")

    return frames
