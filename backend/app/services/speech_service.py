"""
Azure Speech Service — Token vending for the Teams panel.
Exchanges the Speech API key for a short-lived auth token
so the key never reaches the client.
"""

import httpx
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("services.speech")


async def get_speech_token() -> dict:
    """
    Exchange AZURE_SPEECH_KEY for a short-lived (10-minute) auth token.
    Returns { token: str, region: str }.
    """
    settings = get_settings()

    if not settings.AZURE_SPEECH_KEY or "your" in settings.AZURE_SPEECH_KEY.lower():
        raise ValueError("AZURE_SPEECH_KEY is not configured properly.")

    token_url = (
        f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com"
        f"/sts/v1.0/issueToken"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, headers=headers, content="")

        if response.status_code == 200:
            token = response.text
            logger.info(f"✓ Speech token obtained (region: {settings.AZURE_SPEECH_REGION})")
            return {"token": token, "region": settings.AZURE_SPEECH_REGION}
        else:
            logger.error(f"✗ Speech token request failed: {response.status_code} — {response.text}")
            raise Exception(f"Speech token request failed with status {response.status_code}")

    except Exception as e:
        logger.error(f"✗ Speech token exchange error: {e}", exc_info=True)
        raise
