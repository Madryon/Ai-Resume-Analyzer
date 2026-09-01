# AI Resume Analyzer (ResumePilot)

A Flask + Google Gemini project that analyzes resumes and compares them with job descriptions.

## Features

- Upload PDF, DOCX, or TXT resume
- Paste resume text
- ATS-readiness estimate
- Full resume analysis
- Keyword matching against a job description
- Resume improvement suggestions
- Before/after wording improvements
- Job-match score
- AI-assisted resume rewrite using only supplied facts
- Beginner/professional explanation level
- Local browser history
- Copy and download analysis
- No resume code is executed

## Architecture

Browser → Flask → Google Gemini API → Flask → Browser

## Setup

### 1. Get a Gemini API key

Go to [aistudio.google.com](https://aistudio.google.com), sign in, and create a free API key.

### 2. Create and activate a virtual environment

**macOS/Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Copy `.env.example` to `.env` and fill in your real key:

```
GEMINI_API_KEY=your-real-key-here
GEMINI_MODEL=gemini-3.7-flash
```

`.env` is already excluded from Git via `.gitignore` — never commit it.

### 5. Start the app

```bash
python app.py
```

### 6. Open in your browser

```text
http://127.0.0.1:5000
```

## Important

The ATS score is an AI-based estimate, not a score from a specific commercial ATS.

The application is designed not to invent qualifications or experience. Users should only add skills, achievements, or keywords that are truthful.

## Security notes

- The Gemini API key lives only in `.env` on the server and is never sent to the browser.
- Never commit `.env` to version control.
- When deploying to a host (Render, Railway, etc.), set `GEMINI_API_KEY` as an environment variable in that platform's dashboard instead of uploading `.env`.
