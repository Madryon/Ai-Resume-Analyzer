import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types
from openai import OpenAI

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

# Safe client initialization
gemini_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None


def extract_text(file):
    if not file or not file.filename:
        return ""

    ext = Path(file.filename).suffix.lower()

    if ext == ".txt":
        return file.read().decode("utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(file)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise ValueError(f"Could not read PDF: {e}")

    if ext == ".docx":
        try:
            from docx import Document

            doc = Document(file)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            raise ValueError(f"Could not read DOCX: {e}")

    raise ValueError("Unsupported file type. Use PDF, DOCX, or TXT.")


def call_ai(model, resume, job, mode, level):
    audience = (
        "Use simple language suitable for a college student."
        if level == "beginner"
        else "Use professional language suitable for a job applicant."
    )

    tasks = {
        "full": """Perform a complete resume review. Include:
1. Overall ATS/readability score out of 100
2. Strengths
3. Weaknesses
4. Missing or weak sections
5. Important keywords found
6. Important keywords missing compared with the job description
7. Specific improvement suggestions
8. Formatting/content problems
9. A prioritized action plan""",
        "ats": """Focus on ATS compatibility. Give an ATS score out of 100.
Check section structure, keyword relevance, measurable achievements,
clarity, formatting risks, and job-description alignment.""",
        "keywords": """Compare the resume with the job description.
List matched keywords, missing keywords, related keywords, and skills
that should be added only if the candidate genuinely has them.
Do not encourage lying or inventing experience.""",
        "improve": """Identify weak resume statements and improve them.
For each useful improvement, show:
BEFORE:
AFTER:
REASON:
Do not invent achievements, numbers, employers, degrees, or skills.""",
        "rewrite": """Create an improved version of the resume using only
information already present in the supplied resume. Improve wording,
structure, clarity, and impact without inventing facts.""",
        "jobmatch": """Evaluate how well the resume matches the supplied job
description. Give a match score out of 100, explain the strongest matches,
the biggest gaps, and the highest-priority changes.""",
    }

    task = tasks.get(mode, tasks["full"])

    system = f"""You are an expert resume reviewer and ATS consultant.
{audience}

Rules:
- Never invent qualifications, experience, employers, degrees, certifications, metrics, or skills.
- If a recommendation requires information that is not present, clearly label it as something the user should add only if true.
- Be constructive and specific.
- Use headings, bullets, and tables where useful.
- Do not make decisions based on protected or sensitive personal characteristics.
- Do not claim that your score is the score of a real ATS vendor; it is an AI-based estimate.
"""

    prompt = f"""Analyze this resume.

TASK:
{task}

RESUME:
----------------
{resume[:30000]}
----------------

JOB DESCRIPTION:
----------------
{job[:20000] if job.strip() else "No job description was provided. Evaluate general resume quality and ATS readiness."}
----------------
"""

    # 1. Route to OpenAI Models
    if model.startswith("gpt-") or "openai" in model:
        if not openai_client:
            raise ValueError(
                "OPENAI_API_KEY is not configured in environment variables."
            )

        response = openai_client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        text_output = response.choices[0].message.content or ""
        return text_output, response

    # 2. Route to Google Gemini Models
    else:
        if not client:
            raise ValueError(
                "GEMINI_API_KEY is not configured in environment variables."
            )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.2,
                max_output_tokens=10000,
            ),
        )
        return response.text or "", response


@app.route("/")
def index():
    return render_template("index.html", default_model=DEFAULT_MODEL)


@app.get("/api/health")
def health():
    gemini_ready = bool(os.getenv("GEMINI_API_KEY"))
    openai_ready = bool(os.getenv("OPENAI_API_KEY"))

    if not gemini_ready and not openai_ready:
        return (
            jsonify(
                {"ok": False, "error": "No API keys configured", "models": []}
            ),
            503,
        )

    available_models = [DEFAULT_MODEL]
    if openai_ready:
        available_models.append("gpt-4o-mini")

    return jsonify({"ok": True, "models": available_models})


@app.post("/api/analyze")
def analyze():
    try:
        resume = (request.form.get("resume_text") or "").strip()
        job = (request.form.get("job_description") or "").strip()
        mode = request.form.get("mode", "full")
        level = request.form.get("level", "normal")
        model = (request.form.get("model") or DEFAULT_MODEL).strip()

        uploaded = request.files.get("resume_file")
        if not resume and uploaded and uploaded.filename:
            resume = extract_text(uploaded).strip()

        if not resume:
            return (
                jsonify(
                    {
                        "error": "Paste your resume or upload a PDF, DOCX, or TXT file."
                    }
                ),
                400,
            )

        if len(resume) < 80:
            return (
                jsonify(
                    {"error": "The resume text is too short to analyze."}
                ),
                400,
            )

        answer, raw = call_ai(model, resume, job, mode, level)

        input_tokens = 0
        output_tokens = 0

        if raw:
            # Check Gemini usage metadata
            if hasattr(raw, "usage_metadata") and raw.usage_metadata:
                input_tokens = getattr(
                    raw.usage_metadata, "prompt_token_count", 0
                )
                output_tokens = getattr(
                    raw.usage_metadata, "candidates_token_count", 0
                )
            # Check OpenAI usage metadata
            elif hasattr(raw, "usage") and raw.usage:
                input_tokens = getattr(raw.usage, "prompt_tokens", 0)
                output_tokens = getattr(raw.usage, "completion_tokens", 0)

        return jsonify(
            {
                "answer": answer,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"AI API error: {e}"}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
