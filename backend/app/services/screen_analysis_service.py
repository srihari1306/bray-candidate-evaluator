"""
Screen Analysis Service — analyzes screen recording frames for suspicious URLs
(via OCR) and suspicious objects using Azure Computer Vision.
"""

import asyncio

from app.config import get_settings
from app.models.proctoring_models import ScreenSignals
from app.services.frame_extraction_service import extract_frames
from app.services.computer_vision_service import analyze_frame_for_text, analyze_frame_for_people
from app.utils.logger import get_logger

logger = get_logger("services.screen_analysis")

# Object labels considered suspicious on a screen recording
SUSPICIOUS_OBJECT_LABELS = [
    "cell phone", "mobile phone", "smartphone", "telephone", "book", "paper"
]


async def analyze_screen_recording(blob_name: str) -> ScreenSignals:
    """
    Analyze a screen recording for suspicious URLs and objects.

    Extracts frames, runs OCR + object detection on each, checks for suspicious
    domain names in text and suspicious physical objects in the scene.

    Args:
        blob_name: The blob name of the screen recording (e.g., "session_uuid_screen.webm")

    Returns:
        ScreenSignals with all fields populated.
    """
    if not blob_name:
        return ScreenSignals()

    settings = get_settings()
    interval = settings.PROCTORING_FRAME_INTERVAL_SECONDS
    suspicious_domains = [d.strip().lower() for d in settings.PROCTORING_SUSPICIOUS_DOMAINS.split(",") if d.strip()]

    # Extract frames
    frames = await extract_frames(blob_name, interval)
    if not frames:
        return ScreenSignals()

    total_frames = len(frames)
    semaphore = asyncio.Semaphore(3)

    found_urls: set[str] = set()
    found_labels: set[str] = set()
    suspicious_frame_count = 0
    suspicious_frame_lock = asyncio.Lock()

    async def _analyze_frame(idx: int, frame_bytes: bytes):
        nonlocal suspicious_frame_count

        async with semaphore:
            frame_suspicious = False

            try:
                # Run OCR and object detection in parallel
                text_result, obj_result = await asyncio.gather(
                    analyze_frame_for_text(frame_bytes),
                    analyze_frame_for_people(frame_bytes),
                )

                # Extract text from OCR result
                text_parts = []
                blocks = text_result.get("readResult", {}).get("blocks", [])
                for block in blocks:
                    for line in block.get("lines", []):
                        line_text = line.get("text", "")
                        if line_text:
                            text_parts.append(line_text)

                full_text = " ".join(text_parts).lower()

                # Check for suspicious domains in text
                for domain in suspicious_domains:
                    if domain in full_text:
                        found_urls.add(domain)
                        frame_suspicious = True

                # Check for suspicious objects
                objects = obj_result.get("objectsResult", {}).get("values", [])
                for obj in objects:
                    obj_name = obj.get("name", "").lower()
                    confidence = obj.get("confidence", 0)
                    if confidence > 0.7 and obj_name in SUSPICIOUS_OBJECT_LABELS:
                        found_labels.add(obj_name)
                        frame_suspicious = True

            except Exception as e:
                logger.warning(f"Screen frame {idx} analysis failed: {e}")

            if frame_suspicious:
                async with suspicious_frame_lock:
                    suspicious_frame_count += 1

    # Analyze all frames with concurrency limit
    tasks = [_analyze_frame(idx, frame) for idx, frame in enumerate(frames)]
    await asyncio.gather(*tasks)

    logger.info(
        f"Screen analysis complete for {blob_name}: "
        f"{total_frames} frames analyzed, {suspicious_frame_count} suspicious, "
        f"URLs: {found_urls}, Labels: {found_labels}"
    )

    return ScreenSignals(
        suspicious_urls_detected=sorted(found_urls),
        suspicious_labels=sorted(found_labels),
        suspicious_frame_count=suspicious_frame_count,
        frames_analyzed=total_frames,
    )
