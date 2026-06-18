"""
Camera Analysis Service — analyzes camera recording frames for face presence
and multiple-person detection using Azure Computer Vision.
"""

import asyncio

from app.config import get_settings
from app.models.proctoring_models import CameraSignals
from app.services.frame_extraction_service import extract_frames
from app.services.computer_vision_service import analyze_frame_for_people
from app.utils.logger import get_logger

logger = get_logger("services.camera_analysis")
import logging
logger.setLevel(logging.DEBUG)


def _frame_to_timestamp(frame_idx: int, interval_seconds: int) -> str:
    """Convert frame index to MM:SS timestamp string."""
    total_seconds = frame_idx * interval_seconds
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


async def analyze_camera_recording(blob_name: str) -> CameraSignals:
    """
    Analyze a camera recording for face presence and multiple people.

    Extracts frames from the recording, sends each to Azure CV for people/object
    detection, and builds CameraSignals with face coverage, multi-face segments,
    and face-absent segments.

    Args:
        blob_name: The blob name of the camera recording (e.g., "session_uuid_camera.webm")

    Returns:
        CameraSignals with all fields populated.
    """
    if not blob_name:
        return CameraSignals()

    settings = get_settings()
    interval = settings.PROCTORING_FRAME_INTERVAL_SECONDS

    # Extract frames
    frames = await extract_frames(blob_name, interval)
    if not frames:
        return CameraSignals()

    total_frames = len(frames)
    semaphore = asyncio.Semaphore(3)

    # Per-frame face counts
    face_counts: list[int] = [0] * total_frames

    async def _analyze_frame(idx: int, frame_bytes: bytes):
        async with semaphore:
            try:
                result = await analyze_frame_for_people(frame_bytes)

                # DEBUG — log raw CV response for first 5 frames only
                if idx < 5:
                    people = result.get("peopleResult", {}).get("values", [])
                    objects = result.get("objectsResult", {}).get("values", [])
                    
                    logger.debug(f"Frame {idx} — peopleResult count: {len(people)}")
                    for i, p in enumerate(people):
                        logger.debug(f"  Person {i}: confidence={p.get('confidence', 0):.3f}, bbox={p.get('boundingBox', {})}")
                    
                    logger.debug(f"Frame {idx} — objectsResult count: {len(objects)}")
                    for i, o in enumerate(objects):
                        logger.debug(f"  Object {i}: name={o.get('name')}, confidence={o.get('confidence', 0):.3f}")

                # Fixed — use peopleResult as primary, filter by confidence
                people = result.get("peopleResult", {}).get("values", [])
                
                # Filter people by confidence threshold
                confident_people = [p for p in people if p.get("confidence", 0) > 0.85]
                
                # Only use objectsResult as secondary if peopleResult is empty
                if not confident_people:
                    objects = result.get("objectsResult", {}).get("values", [])
                    person_objects = [
                        o for o in objects 
                        if o.get("name", "").lower() == "person" 
                        and o.get("confidence", 0) > 0.85
                    ]
                    face_count = len(person_objects)
                else:
                    face_count = len(confident_people)
                    
                logger.debug(f"Frame {idx} — face_count={face_count} (people={len(people)})")
                
                face_counts[idx] = face_count

            except Exception as e:
                logger.warning(f"Camera frame {idx} analysis failed: {e}")
                face_counts[idx] = 0

    # Analyze all frames with concurrency limit
    tasks = [_analyze_frame(idx, frame) for idx, frame in enumerate(frames)]
    await asyncio.gather(*tasks)

    # Compute metrics
    frames_with_face = sum(1 for c in face_counts if c >= 1)
    face_coverage_percent = round((frames_with_face / total_frames) * 100, 1) if total_frames > 0 else 0.0
    multiple_faces_detected = any(c >= 2 for c in face_counts)

    # Build face-absent segments
    face_absent_segments: list[dict] = []
    absent_start = None
    for idx, count in enumerate(face_counts):
        if count == 0:
            if absent_start is None:
                absent_start = idx
        else:
            if absent_start is not None:
                face_absent_segments.append({
                    "start": _frame_to_timestamp(absent_start, interval),
                    "end": _frame_to_timestamp(idx - 1, interval),
                })
                absent_start = None
    # Close any open absent segment at the end
    if absent_start is not None:
        face_absent_segments.append({
            "start": _frame_to_timestamp(absent_start, interval),
            "end": _frame_to_timestamp(total_frames - 1, interval),
        })

    # Build multiple-faces segments
    multiple_faces_segments: list[dict] = []
    multi_start = None
    consecutive_multi = 0
    MULTI_FACE_MIN_CONSECUTIVE = 2

    for idx, count in enumerate(face_counts):
        if count >= 2:
            consecutive_multi += 1
            if consecutive_multi >= MULTI_FACE_MIN_CONSECUTIVE and multi_start is None:
                # Start segment from the first frame in the consecutive sequence
                multi_start = idx - MULTI_FACE_MIN_CONSECUTIVE + 1
        else:
            consecutive_multi = 0
            if multi_start is not None:
                multiple_faces_segments.append({
                    "start": _frame_to_timestamp(multi_start, interval),
                    "end": _frame_to_timestamp(idx - 1, interval),
                })
                multi_start = None

    # Close any open multi-face segment at the end
    if multi_start is not None:
        multiple_faces_segments.append({
            "start": _frame_to_timestamp(multi_start, interval),
            "end": _frame_to_timestamp(total_frames - 1, interval),
        })

    logger.info(
        f"Camera analysis complete for {blob_name}: "
        f"{total_frames} frames, {face_coverage_percent}% coverage, "
        f"{len(face_absent_segments)} absent segments, "
        f"{len(multiple_faces_segments)} multi-face segments"
    )

    return CameraSignals(
        face_coverage_percent=face_coverage_percent,
        multiple_faces_detected=multiple_faces_detected,
        multiple_faces_segments=multiple_faces_segments,
        face_absent_segments=face_absent_segments,
        frames_analyzed=total_frames,
    )
