import asyncio
from app.models.schemas import EvaluationRequest, SkillCategory
from app.services.evaluation_service import get_evaluation_engine

async def main():
    try:
        req = EvaluationRequest(
            job_description="We need a Senior AI Engineer with strong cloud infrastructure, agentic AI, and Linux skills. Must have experience with Kubernetes, LangChain, and Bash scripting.",
            job_title="Senior AI Engineer",
            skills=[
                SkillCategory(name="Cloud Engineering", weight=40),
                SkillCategory(name="Agentic AI", weight=35),
                SkillCategory(name="Terminal/Linux", weight=25),
            ],
            max_candidates=50,
            reindex=False
        )
        engine = get_evaluation_engine()
        res = await engine.evaluate(req)
        print("Status:", res.status)
        print("Candidates:", len(res.candidates))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
