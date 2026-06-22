"""
Frame Extraction Service — downloads recordings and extracts frames via ffmpeg.
"""

import asyncio
import os
import glob
import tempfile

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
    3. Writes to a temp directory and runs ffmpeg to extract JPEG frames.
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

    # Extract frames using ffmpeg in a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use blob_name to make temp file unique so parallel extractions don't collide
        safe_name = blob_name.replace("/", "_").replace("\\", "_")
        input_path = os.path.join(tmpdir, f"{safe_name}.webm")
        output_pattern = os.path.join(tmpdir, "frame_%04d.jpg")

        # Write video bytes to temp file
        with open(input_path, "wb") as f:
            f.write(video_bytes)

        # Run ffmpeg asynchronously
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"fps=1/{interval_seconds}",
            "-q:v", "2",
            output_pattern,
            "-y",
            "-loglevel", "error",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                stderr_text = stderr.decode("utf-8", errors="replace")
                logger.error(f"ffmpeg failed for {blob_name} (exit code {process.returncode}): {stderr_text}")
                return []

        except FileNotFoundError:
            logger.error("ffmpeg not found in PATH — cannot extract frames")
            return []
        except Exception as e:
            logger.error(f"ffmpeg execution error for {blob_name}: {e}", exc_info=True)
            return []

        # Read extracted frame files in sorted order
        frame_files = sorted(glob.glob(os.path.join(tmpdir, "frame_*.jpg")))
        frames = []
        for frame_file in frame_files:
            with open(frame_file, "rb") as f:
                frames.append(f.read())

        logger.info(f"Extracted {len(frames)} frames from {blob_name}")
        return frames
