# PrepSensei — AI Placement Prep Agent

> Multi-agent AI system that analyzes your resume, conducts a real mock interview, and builds a personalized study plan — powered by LangGraph, LLaMA 3, and RAG.

![PrepSensei](https://img.shields.io/badge/LangGraph-Multi--Agent-7c6aff?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-LLaMA%203-06d6a0?style=for-the-badge)
![RAG](https://img.shields.io/badge/RAG-ChromaDB-f4a261?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge)

---

## What It Does

Most college students go into placement season with zero structured preparation. PrepSensei solves this — upload your resume, select your target company and role, and the system does the rest.

1. **Reads your resume** and extracts your current technical skills
2. **Retrieves real interview questions** from a curated database + live web search fallback
3. **Identifies your skill gaps** by comparing your profile against what the role actually needs
4. **Conducts a full mock interview** — 10 to 15 questions, one at a time
5. **Evaluates every answer** with a score out of 10, specific feedback, and what a perfect answer looks like
6. **Builds a personalized study plan** for 20, 30, 45, or 60 days based on your weak areas
7. **Generates a downloadable PDF report** with everything in one place

---

## Architecture

```
User (Browser)
      │
      ▼
index.html (Dark Theme UI — HTML/CSS/JS)
      │
      ▼
FastAPI Backend (api.py)
      │
      ├── utils.py ──────── PDF resume parser + PDF report generator
      │
      ├── rag.py ─────────── ChromaDB question bank + DuckDuckGo web fallback
      │
      └── agent.py ──────── LangGraph orchestrating 4 agents
                │
                ├── Agent 1: Analyzer ── reads resume, finds skill gaps
                ├── Agent 2: Interviewer ── asks questions one by one
                ├── Agent 3: Coach ── scores each answer with feedback
                └── Agent 4: Planner ── builds personalized study plan
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | LLaMA 3 via Groq API (free tier) |
| Agent Orchestration | LangGraph |
| Vector Database | ChromaDB (local, persistent) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, runs on CPU) |
| Web Search Fallback | DuckDuckGo Search (no API key needed) |
| Backend | FastAPI + Uvicorn |
| PDF Parsing | PyMuPDF (fitz) |
| PDF Generation | ReportLab |
| Frontend | Vanilla HTML + CSS + JavaScript (dark theme) |

---

## Key Features

- **Smart question retrieval** — searches local ChromaDB first, falls back to live web search (Glassdoor, GeeksForGeeks, InterviewBit) if company not in database, shows the source of every question
- **Honest gap analysis** — hardcoded role skill maps ensure relevant missing skills (no hallucinated suggestions like HTML for AI Engineer roles)
- **Flexible study plan duration** — user picks 20, 30, 45, or 60 days before the interview starts
- **Web search fallback** — works for any company, not just ones in the local database
- **Downloadable PDF report** — full feedback + study plan in one shareable document
- **Zero cost** — runs entirely on free tiers (Groq free API, ChromaDB local, Render free, GitHub Pages free)

---

## How to Run Locally

**Prerequisites:** Python 3.10+, Git

```bash
# clone the repo
git clone https://github.com/nilj07/prepsensei.git
cd prepsensei

# create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# install dependencies
pip install -r requirements.txt

# add your Groq API key
# get free key at console.groq.com
echo "GROQ_API_KEY=your_key_here" > .env

# build question bank (run once)
python rag.py

# start backend (Terminal 1)
uvicorn api:app --reload --port 8000

# serve frontend (Terminal 2)
python -m http.server 5500
```

Open `http://localhost:5500/index.html` in your browser.

---

## Project Structure

```
prepsensei/
├── index.html          ← dark theme frontend (HTML/CSS/JS)
├── api.py              ← FastAPI backend, session management
├── agent.py            ← all 4 LangGraph agents
├── rag.py              ← ChromaDB setup, question retrieval, web fallback
├── utils.py            ← resume parser, PDF report generator
├── questions.json      ← 30 curated interview questions (expandable)
├── .env                ← API keys (not committed)
└── requirements.txt
```

---

## Supported Companies and Roles

**Companies in local database:**
Sarvam AI, Razorpay, CRED, Fractal Analytics + Generic questions for all companies

**Roles:**
LLM Engineer, Agentic AI Engineer, AI Engineer, Backend Engineer, Data Scientist, ML Engineer

**Any other company or role** → automatically triggers web search and fetches questions live from Glassdoor, GeeksForGeeks, and InterviewBit.

---

## Sample Output

**Gap Analysis:**
- Readiness Score: 42/100
- Skills Found: Python, FastAPI, Docker, SQL
- Skills to Build: RAG Systems, LangGraph, LLM Fine-tuning, Vector Databases, Prompt Engineering

**Per-Answer Feedback (Agent 3):**
```
SCORE: 6/10
GOOD: Correctly identified that RAG reduces hallucination
MISSING: Did not mention chunking strategy or reranking
IDEAL: A complete answer covers the full pipeline — ingest, chunk,
embed, store, retrieve, rerank, generate — and explains why each
step exists
```

**30-Day Study Plan (Agent 4):**
```
Week 1: RAG fundamentals — build a document Q&A system with ChromaDB
Week 2: LangGraph and agents — build a ReAct agent with tool calling
Week 3: Fine-tuning — QLoRA on a small model with Hugging Face PEFT
Week 4: System design — design a production RAG system end to end
```

---

## What I Learned Building This

- How to orchestrate multiple LLM agents using LangGraph state graphs with conditional routing
- Why hardcoded role skill maps produce more reliable results than asking the LLM what a role needs
- How to combine local vector search (ChromaDB) with live web search as a fallback — the retrieval pattern used in production RAG systems
- FastAPI session management for multi-turn stateful applications
- How prompt structure affects output quality — structured output formats (SCORE: / MISSING: / GOOD:) are far more reliable than free-form LLM responses


---

## Author

**Nilesh** — Final Year CSE Student, Kolhapur
- GitHub: [github.com/nilj07](https://github.com/nilj07)
- LinkedIn: [linkedin.com/in/nilesh-jadhav-715817213](https://linkedin.com/in/nilesh-jadhav-715817213)

---

*Built as part of my journey to become an Agentic AI / LLM Engineer*
