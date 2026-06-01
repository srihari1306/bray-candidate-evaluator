"""
LLM prompt templates for resume evaluation and parsing.
All prompts are centralized here for easy iteration and testing.
"""

RESUME_PARSING_PROMPT = """You are an expert HR resume parser. Extract structured information from the following resume text.

Return a JSON object with these fields:
- name: string (candidate's full name)
- email: string (email address, empty string if not found)
- phone: string (phone number, empty string if not found)
- skills: string[] (list of technical and soft skills mentioned)
- experience_years: number or null (estimated total years of experience)
- education: string[] (degrees and institutions)
- certifications: string[] (professional certifications)
- work_history: string[] (company names and roles, most recent first)
- projects: string[] (notable projects described)
- technologies: string[] (specific technologies, tools, frameworks mentioned)

Resume Text:
{resume_text}

Return ONLY valid JSON, no markdown formatting or extra text."""


CANDIDATE_EVALUATION_PROMPT = """You are an expert technical recruiter performing a detailed evaluation of a candidate's resume against a job description.

## Job Description
{job_description}

## Custom Skill Categories to Evaluate
{skill_categories}

## Candidate Resume
{resume_text}

## Instructions
Evaluate this candidate thoroughly using semantic understanding, NOT simple keyword matching.

For each custom skill category, look for:
- Direct mentions of relevant technologies
- Related frameworks, tools, and methodologies
- Project experience demonstrating the skill
- Indirect evidence (e.g., "LangChain" implies Agentic AI experience)

## Scoring Guidelines
- 90-100: Expert level, extensive direct experience with strong evidence
- 75-89: Strong experience with clear evidence
- 60-74: Moderate experience, some evidence
- 40-59: Limited experience, indirect evidence only
- 0-39: Little to no evidence found

## Evaluation Criteria Weights
- Skills Match: 40%
- Experience Relevance: 25%
- Projects/Portfolio: 15%
- Education: 10%
- Certifications: 10%

Return a JSON object with this exact structure:
{{
    "candidate_name": "string",
    "overall_score": number (0-100),
    "overall_recommendation": "Strong Match" | "Good Match" | "Moderate Match" | "Weak Match" | "Not Recommended",
    "skill_scores": [
        {{
            "skill": "skill category name",
            "score": number (0-100),
            "confidence": "High" | "Medium" | "Low",
            "evidence": ["string array of specific evidence from the resume"]
        }}
    ],
    "missing_skills": ["string array of skills from JD not found in resume"],
    "strengths": ["string array of candidate's key strengths"],
    "weaknesses": ["string array of areas for improvement"],
    "summary": "2-3 sentence summary of the candidate's fit",
    "recommendation": "1-2 sentence hiring recommendation",
    "interview_questions": ["3-5 targeted interview questions based on gaps or areas to probe"]
}}

Return ONLY valid JSON, no markdown formatting or extra text."""


SKILL_CATEGORY_FORMAT = """
Skill Category: {skill_name}
Weight: {skill_weight}%
Related technologies and concepts to look for:
{related_concepts}
"""


# Semantic skill mapping — helps the LLM understand what to look for
SKILL_SEMANTIC_MAP: dict[str, list[str]] = {
    "Cloud Engineering": [
        "Azure", "AWS", "GCP", "Google Cloud", "Kubernetes", "K8s", "Docker",
        "Terraform", "CloudFormation", "Pulumi", "DevOps", "CI/CD",
        "Infrastructure as Code", "IaC", "Cloud Architecture", "Serverless",
        "Lambda", "Azure Functions", "ECS", "EKS", "AKS", "Helm",
        "Cloud Security", "VPC", "Networking", "Load Balancing", "Auto Scaling",
        "Cloud Migration", "Microservices", "Service Mesh", "Istio",
    ],
    "Agentic AI": [
        "LangChain", "LangGraph", "CrewAI", "AutoGen", "Autogen",
        "Tool Calling", "Function Calling", "RAG", "Retrieval Augmented Generation",
        "Multi-Agent", "Agent Orchestration", "AI Agents", "Autonomous Agents",
        "MCP", "Model Context Protocol", "Prompt Engineering", "Chain of Thought",
        "ReAct", "AI Pipeline", "LLM Orchestration", "Semantic Kernel",
        "AI Workflow", "Planning Agent", "Reasoning Agent",
    ],
    "Terminal/Linux": [
        "Bash", "Shell", "Zsh", "SSH", "Linux", "Ubuntu", "CentOS", "RHEL",
        "Docker CLI", "Git CLI", "Command Line", "Terminal", "Scripting",
        "System Administration", "Cron", "Systemd", "Package Management",
        "apt", "yum", "dnf", "grep", "awk", "sed", "vim", "tmux",
        "Linux Administration", "File Systems", "Networking CLI", "curl", "wget",
    ],
    "Machine Learning": [
        "TensorFlow", "PyTorch", "Scikit-learn", "Keras", "XGBoost",
        "Neural Networks", "Deep Learning", "NLP", "Computer Vision",
        "Model Training", "Feature Engineering", "MLOps", "Model Deployment",
        "Hugging Face", "Transformers", "Fine-tuning", "Transfer Learning",
    ],
    "Data Engineering": [
        "Apache Spark", "Kafka", "Airflow", "ETL", "ELT", "Data Pipeline",
        "Data Warehouse", "Snowflake", "BigQuery", "Databricks", "dbt",
        "Data Lake", "Delta Lake", "Apache Beam", "Data Modeling",
        "SQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
    ],
    "Full Stack Development": [
        "React", "Angular", "Vue", "Next.js", "Node.js", "Express",
        "TypeScript", "JavaScript", "Python", "FastAPI", "Django", "Flask",
        "REST API", "GraphQL", "HTML", "CSS", "Responsive Design",
        "Database Design", "ORM", "Authentication", "Authorization",
    ],
}


def get_skill_context(skill_name: str) -> str:
    """Get related concepts for a skill category to enhance LLM understanding."""
    # Check for exact match first
    if skill_name in SKILL_SEMANTIC_MAP:
        return ", ".join(SKILL_SEMANTIC_MAP[skill_name])

    # Check for partial match
    skill_lower = skill_name.lower()
    for key, concepts in SKILL_SEMANTIC_MAP.items():
        if skill_lower in key.lower() or key.lower() in skill_lower:
            return ", ".join(concepts)

    # Return generic guidance
    return f"Any technologies, tools, frameworks, projects, or experience related to {skill_name}"


def build_evaluation_prompt(
    job_description: str,
    resume_text: str,
    skills: list[dict[str, any]],
) -> str:
    """Build the full evaluation prompt with skill categories."""
    skill_sections = []
    for skill in skills:
        context = get_skill_context(skill["name"])
        skill_sections.append(
            SKILL_CATEGORY_FORMAT.format(
                skill_name=skill["name"],
                skill_weight=skill.get("weight", 0),
                related_concepts=context,
            )
        )

    skill_categories_text = "\n".join(skill_sections) if skill_sections else "No specific skill categories defined. Evaluate based on overall JD match."

    return CANDIDATE_EVALUATION_PROMPT.format(
        job_description=job_description,
        skill_categories=skill_categories_text,
        resume_text=resume_text,
    )
