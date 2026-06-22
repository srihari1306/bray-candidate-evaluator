"""
Interview Answer Evaluation Service using Azure OpenAI GPT-4.
Evaluates each candidate answer on Relevance, Clarity, and Depth.
Reuses the same Azure OpenAI client pattern as the resume evaluation engine.
"""

import json
from typing import Optional

from app.config import get_settings
from app.db.session_db import get_interview_db
from app.utils.logger import get_logger

logger = get_logger("services.interview_evaluation")

# ─── System prompt for answer evaluation ───
EVALUATION_SYSTEM_PROMPT = """You are an expert interviewer and talent evaluator.
Your task is to evaluate a candidate's spoken answer to an interview question.
Evaluate on three criteria:
- Relevance: Does it answer the question?
- Clarity: Is it well-structured and easy to understand?
- Depth: Does it demonstrate genuine knowledge or experience?

Return ONLY a JSON object with no other text:
{ "score": <integer 0-10>, "reasoning": "<one concise sentence>" }"""


def _get_openai_client():
    """Get the Azure OpenAI client (lazy initialization)."""
    from openai import AzureOpenAI
    settings = get_settings()
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )


async def evaluate_single_answer(question_text: str, transcript: str) -> dict:
    """
    Evaluate a single answer using GPT-4.
    Returns { score: int, reasoning: str }.
    """
    settings = get_settings()

    if not transcript or transcript.strip() == "":
        logger.warning("Empty transcript — assigning score 0")
        return {"score": 0, "reasoning": "No answer provided."}

    # Fail hard if Azure OpenAI is not configured
    if (not settings.AZURE_OPENAI_API_KEY or 
        "your-" in settings.AZURE_OPENAI_API_KEY or 
        not settings.AZURE_OPENAI_ENDPOINT or 
        "your-" in settings.AZURE_OPENAI_ENDPOINT):
        raise ValueError("Azure OpenAI credentials are not properly configured.")

    user_prompt = f"Interview Question: {question_text}\nCandidate Answer: {transcript}"

    import asyncio
    client = _get_openai_client()
    
    # Run blocking OpenAI call in a background thread to keep event loop free
    def _execute_api():
        return client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=200,
        )

    response = await asyncio.to_thread(_execute_api)
    result_text = response.choices[0].message.content
    result = json.loads(result_text)

    score = max(0, min(10, int(result.get("score", 5))))
    reasoning = result.get("reasoning", "No reasoning provided.")

    logger.info(f"  ✓ Evaluated: score={score}/10 — {reasoning[:60]}...")
    return {"score": score, "reasoning": reasoning}


async def evaluate_answers(session_id: str, answers: list[dict]) -> Optional[dict]:
    """
    Evaluate all interview answers and update the session in the database.

    Args:
        session_id: The interview session ID
        answers: List of { question_index, question_text, transcript }

    Returns:
        Updated session document with scores, or None on failure.
    """
    logger.info(f"──── Evaluating Interview Answers ────")
    logger.info(f"  Session: {session_id}")
    logger.info(f"  Answers to evaluate: {len(answers)}")

    db = get_interview_db()
    scored_answers = []

    for answer in answers:
        question_text = answer.get("question_text", "")
        transcript = answer.get("transcript", "")
        question_index = answer.get("question_index", 0)

        logger.info(f"  Evaluating Q{question_index + 1}: {question_text[:50]}...")

        result = await evaluate_single_answer(question_text, transcript)

        scored_answers.append({
            "question_index": question_index,
            "question_text": question_text,
            "transcript": transcript,
            "score": result["score"],
            "score_reasoning": result["reasoning"],
        })

    # Compute final score
    if scored_answers:
        total = sum(a["score"] for a in scored_answers)
        final_score = round(total / len(scored_answers), 1)
    else:
        final_score = 0.0

    logger.info(f"  Final Score: {final_score}/10")
    logger.info(f"──────────────────────────────────────")

    # Get session to find candidate_id for the partition key
    session = await db.get_session(session_id)
    if not session:
        logger.error(f"Session {session_id} not found — cannot update with scores")
        return None

    candidate_id = session["candidate_id"]

    # Update session in database
    from datetime import datetime
    updates = {
        "answers": scored_answers,
        "final_score": final_score,
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
    }

    try:
        updated = await db.update_session(session_id, candidate_id, updates)
        logger.info(f"✓ Session {session_id} marked as completed with score {final_score}")
        return updated
    except Exception as e:
        logger.error(f"✗ Failed to update session {session_id}: {e}", exc_info=True)
        return None
