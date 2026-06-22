
import json
from typing import Optional

from app.config import get_settings
from app.utils.logger import get_logger
from app.models.proctoring_models import TranscriptSignals

logger = get_logger("services.transcript_proctoring")

def _get_openai_client():
    """Get the Azure OpenAI client (lazy initialization)."""
    from openai import AzureOpenAI
    settings = get_settings()
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )

async def analyze_transcript(answers: list) -> TranscriptSignals:
    """
    Analyze transcript for cheating signs.
    """
    settings = get_settings()

    if not answers:
        return TranscriptSignals(suspicion_score=0, reasoning="No transcripts provided.")

    if (not settings.AZURE_OPENAI_API_KEY or 
        "your-" in settings.AZURE_OPENAI_API_KEY or 
        not settings.AZURE_OPENAI_ENDPOINT or 
        "your-" in settings.AZURE_OPENAI_ENDPOINT):
        logger.warning("Azure OpenAI not configured. Returning default transcript signals.")
        return TranscriptSignals(suspicion_score=0, reasoning="Skipped analysis (OpenAI not configured).")

    # Build transcript text
    transcript_text = ""
    for idx, ans in enumerate(answers):
        q = ans.get("question_text", f"Question {idx+1}")
        t = ans.get("transcript", "")
        transcript_text += f"Q{idx+1}: {q}\nA{idx+1}: {t}\n\n"

    system_prompt = """You are an interview proctoring system. Analyze these spoken interview transcripts for signs that answers were AI-generated, copied, or read from an external source rather than spoken naturally.

Score the suspicion level from 0-10 where:
0-3: Natural spoken answers with filler words, self-corrections, incomplete sentences
4-6: Somewhat structured but could be a prepared candidate
7-10: Unnaturally perfect, structured like written text, no spoken language markers

Respond in JSON only:
{
  "suspicion_score": <integer 0-10>,
  "reasoning": "brief explanation"
}"""

    user_prompt = f"Transcripts:\n{transcript_text}"

    try:
        import asyncio
        client = _get_openai_client()
        
        def _execute_api():
            return client.chat.completions.create(
                model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=200,
            )

        response = await asyncio.to_thread(_execute_api)
        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        score = max(0, min(10, int(result.get("suspicion_score", 0))))
        reasoning = result.get("reasoning", "No reasoning provided.")

        return TranscriptSignals(suspicion_score=score, reasoning=reasoning)

    except Exception as e:
        import openai
        if isinstance(e, openai.BadRequestError) and "content_filter" in str(e):
            logger.warning(f"Transcript content flagged by safety filter: {e}")
            return TranscriptSignals(
                suspicion_score=10, 
                reasoning="Transcript analysis blocked: the candidate's answer contained highly inappropriate or explicit language that triggered the AI safety filter."
            )
            
        logger.error(f"Transcript proctoring failed: {e}", exc_info=True)
        return TranscriptSignals(suspicion_score=0, reasoning="Analysis failed due to an error.")
