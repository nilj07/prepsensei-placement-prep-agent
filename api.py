# api.py
# run with: uvicorn api:app --reload --port 8000

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import tempfile
import os
import json

from utils import read_resume, generate_pdf_report
from rag import build_question_bank
from agent import run_analysis, run_evaluation

app = FastAPI()

# allow frontend to talk to backend
# CORS lets our HTML file (different port) call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# build question bank when server starts
build_question_bank()

# store session data in memory
# in production this would be a database
# for portfolio demo, memory is fine
sessions = {}


@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    student_name: str = Form(...),
    company: str = Form(...),
    role: str = Form(...),
    plan_days: int = Form(30)
):
    # save uploaded PDF to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await resume.read()
        tmp.write(content)
        tmp_path = tmp.name

    # read resume text
    resume_text = read_resume(tmp_path)
    os.unlink(tmp_path)

    if not resume_text:
        return {"error": "Could not read PDF. Use a text-based PDF."}

    # run agent 1
    result = run_analysis(resume_text, company, role, student_name, plan_days)

    # create session id to track this student's data
    session_id = f"{student_name}_{company}".replace(" ", "_").lower()
    sessions[session_id] = result

    return {
        "session_id": session_id,
        "student_name": student_name,
        "company": company,
        "role": role,
        "plan_days": plan_days,
        "readiness_score": result['readiness_score'],
        "gap_summary": result['gap_summary'],
        "skills_found": result['skills_found'],
        "skills_missing": result['skills_missing'],
        "questions": result['questions'],
        "question_sources": result['question_sources'],
        "total_questions": len(result['questions'])
    }


class AnswersPayload(BaseModel):
    session_id: str
    answers: List[str]


@app.post("/evaluate")
async def evaluate(payload: AnswersPayload):
    session = sessions.get(payload.session_id)
    if not session:
        return {"error": "Session not found. Please restart."}

    # add answers to state
    state_with_answers = {
        **session,
        'student_answers': payload.answers,
        'questions_asked': session['questions'][:len(payload.answers)],
        'feedback_list': [],
        'scores': [],
        'current_q_index': 0,
    }

    # run agent 3 + agent 4
    result = run_evaluation(state_with_answers)

    # save updated session
    sessions[payload.session_id] = result

    return {
        "feedback_list": result['feedback_list'],
        "scores": result['scores'],
        "avg_score": sum(result['scores']) / len(result['scores']) if result['scores'] else 0,
        "study_plan": result['study_plan'],
        "weak_topics": result['skills_missing']
    }

@app.post("/download-report")
async def download_report(payload: dict):
    session_id = payload.get("session_id")
    session = sessions.get(session_id)
    
    if not session:
        return {"error": "Session not found"}
    
    try:
        # generate pdf
        pdf_path = generate_pdf_report(
            student_name=session.get('student_name', 'Student'),
            company=session.get('company', 'Company'),
            role=session.get('role', 'Role'),
            readiness_score=session.get('readiness_score', 0),
            skills_found=session.get('skills_found', []),
            skills_missing=session.get('skills_missing', []),
            feedback_list=session.get('feedback_list', []),
            study_plan=session.get('study_plan', 'Study plan not generated'),
            plan_days=session.get('plan_days', 30)
        )
        
        # read file as bytes and return directly
        # FileResponse sometimes fails when path is relative
        # reading as bytes and returning is more reliable
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="placement_report_{session.get("company", "report")}.pdf"'
            }
        )
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"PDF generation failed: {str(e)}"}


@app.get("/health")
def health():
    return {"status": "running"}