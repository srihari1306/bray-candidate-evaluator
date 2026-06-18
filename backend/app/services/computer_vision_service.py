"""
Azure Computer Vision Service — image analysis for proctoring.
Uses the Azure Computer Vision 4.0 Image Analysis API.
"""

import httpx

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("services.computer_vision")


async def analyze_frame_for_people(image_bytes: bytes) -> dict:
    """
    Analyze a frame for people and objects using Azure Computer Vision.

    POST to {endpoint}/computervision/imageanalysis:analyze
    Query: api-version=2023-02-01-preview, features=people,objects
    Returns full JSON response.
    """
    settings = get_settings()
    url = f"{settings.AZURE_COMPUTER_VISION_ENDPOINT.rstrip('/')}/computervision/imageanalysis:analyze"

    params = {
        "api-version": "2024-02-01",
        "features": "people,objects",
    }
    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_COMPUTER_VISION_KEY,
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, params=params, headers=headers, content=image_bytes)
        response.raise_for_status()
        result = response.json()
        return result


async def analyze_frame_for_text(image_bytes: bytes) -> dict:
    """
    Analyze a frame for text (OCR) using Azure Computer Vision.

    POST to {endpoint}/computervision/imageanalysis:analyze
    Query: api-version=2023-02-01-preview, features=read
    Returns full JSON response.
    """
    settings = get_settings()
    url = f"{settings.AZURE_COMPUTER_VISION_ENDPOINT.rstrip('/')}/computervision/imageanalysis:analyze"

    params = {
        "api-version": "2024-02-01",
        "features": "read",
    }
    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_COMPUTER_VISION_KEY,
        "Content-Type": "application/octet-stream",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, params=params, headers=headers, content=image_bytes)
        response.raise_for_status()
        result = response.json()
        return result
