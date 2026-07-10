# app.py
# streamlit UI - this is what student sees in browser
# run with: streamlit run app.py

import streamlit as st
import os
import tempfile
from utils import read_resume, generate_pdf_report
from rag import build_question_bank
from agent import run_analysis_only, run_full_interview

# page config
st.set_page_config(
    page_title="AI Placement Prep Agent",
    page_icon="🎯",
    layout="centered"
)

# build question bank on first run
# this only actually does work first time
# after that chromadb loads from disk
build_question_bank()


# ── HEADER ────────────────────────────────────────────────────────
st.title("🎯 AI Placement Prep Agent")
st.markdown("Upload your resume, pick your target company and role, then practice your interview.")
st.divider()


# ── SESSION STATE ─────────────────────────────────────────────────
# streamlit reruns the whole script on every interaction
# session_state saves data between reruns
# without this, all variables reset every time user clicks anything

if 'step' not in st.session_state:
    st.session_state.step = 1  # which step we are on

if 'analysis' not in st.session_state:
    st.session_state.analysis = None  # agent1 results

if 'current_q' not in st.session_state:
    st.session_state.current_q = 0  # which question we are on

if 'answers' not in st.session_state:
    st.session_state.answers = []  # student answers so far

if 'final_result' not in st.session_state:
    st.session_state.final_result = None  # final results after interview


# ── STEP 1: INPUT FORM ────────────────────────────────────────────
if st.session_state.step == 1:
    
    st.subheader("Step 1: Tell us about you")
    
    student_name = st.text_input("Your name", placeholder="Nilesh Patil")
    
    company = st.selectbox(
        "Target company",
        ["Sarvam AI", "Razorpay", "CRED", "Fractal Analytics", "Other"]
    )
    
    # if other, let them type company name
    if company == "Other":
        company = st.text_input("Enter company name", placeholder="Zepto, Swiggy, etc.")
    
    role = st.selectbox(
        "Target role",
        ["LLM Engineer", "AI Engineer", "Backend Engineer", 
         "Agentic AI Engineer", "Data Scientist", "Other"]
    )
    
    if role == "Other":
        role = st.text_input("Enter role", placeholder="ML Engineer, etc.")
    
    resume_file = st.file_uploader(
        "Upload your resume (PDF)",
        type=['pdf']
    )
    
    if st.button("Start Analysis →", type="primary"):
        
        # validate inputs
        if not student_name:
            st.error("Please enter your name")
        elif not company:
            st.error("Please enter company name")
        elif not resume_file:
            st.error("Please upload your resume PDF")
        else:
            # save uploaded PDF to temp file
            # streamlit gives us the file as bytes
            # we save to disk so pymupdf can read it
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(resume_file.read())
                tmp_path = tmp.name
            
            # read resume text
            with st.spinner("Reading your resume..."):
                resume_text = read_resume(tmp_path)
            
            # clean up temp file
            os.unlink(tmp_path)
            
            if not resume_text:
                st.error("Could not read resume. Make sure it is a text-based PDF.")
            else:
                # run agent 1 analysis
                with st.spinner("Analyzing your resume and finding skill gaps... (30-60 seconds)"):
                    analysis = run_analysis_only(
                        resume_text=resume_text,
                        company=company,
                        role=role,
                        student_name=student_name
                    )
                
                # save to session state
                st.session_state.analysis = analysis
                st.session_state.step = 2
                st.rerun()  # refresh page to show step 2


# ── STEP 2: SHOW GAP ANALYSIS ─────────────────────────────────────
elif st.session_state.step == 2:
    
    analysis = st.session_state.analysis
    
    st.subheader(f"Step 2: Your Gap Analysis for {analysis['company']} — {analysis['role']}")
    
    # readiness score
    score = analysis['readiness_score']
    
    # color based on score
    if score >= 70:
        st.success(f"Readiness Score: {score}/100 — You are in good shape!")
    elif score >= 40:
        st.warning(f"Readiness Score: {score}/100 — Some gaps to fill")
    else:
        st.error(f"Readiness Score: {score}/100 — Significant preparation needed")
    
    st.progress(score / 100)
    
    if analysis['gap_summary']:
        st.info(analysis['gap_summary'])
    
    # two columns for skills
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**✅ Skills You Have**")
        for skill in analysis['skills_found']:
            st.markdown(f"• {skill}")
    
    with col2:
        st.markdown("**❌ Skills to Build**")
        for skill in analysis['skills_missing']:
            st.markdown(f"• {skill}")
    
    st.divider()
    
    # show questions that will be asked
    st.markdown(f"**Interview will cover {len(analysis['questions'])} questions:**")
    for i, q in enumerate(analysis['questions']):
        st.markdown(f"{i+1}. {q[:100]}...")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Mock Interview →", type="primary"):
            # reset interview state
            st.session_state.current_q = 0
            st.session_state.answers = []
            st.session_state.step = 3
            st.rerun()
    with col2:
        if st.button("← Start Over"):
            st.session_state.step = 1
            st.session_state.analysis = None
            st.rerun()


# ── STEP 3: MOCK INTERVIEW ────────────────────────────────────────
elif st.session_state.step == 3:
    
    analysis = st.session_state.analysis
    questions = analysis['questions']
    current_q = st.session_state.current_q
    
    # check if all questions answered
    if current_q >= len(questions):
        st.session_state.step = 4
        st.rerun()
    
    st.subheader(f"Step 3: Mock Interview")
    st.caption(f"Question {current_q + 1} of {len(questions)}")
    
    # progress bar for interview
    st.progress((current_q) / len(questions))
    
    # show current question
    st.markdown(f"### Q{current_q + 1}: {questions[current_q]}")
    
    # show previous answers if any
    if st.session_state.answers:
        with st.expander(f"Your previous answers ({len(st.session_state.answers)} answered)"):
            for i, ans in enumerate(st.session_state.answers):
                st.markdown(f"**Q{i+1}:** {questions[i][:60]}...")
                st.markdown(f"**Your answer:** {ans}")
                st.divider()
    
    # answer input
    answer = st.text_area(
        "Your answer:",
        height=150,
        placeholder="Type your answer here. Take your time, think clearly...",
        key=f"answer_{current_q}"  # unique key per question so it resets
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("Submit Answer →", type="primary"):
            if not answer.strip():
                st.error("Please write an answer before submitting")
            else:
                # save answer
                st.session_state.answers.append(answer)
                st.session_state.current_q += 1
                st.rerun()
    
    with col2:
        if st.button("Skip Question"):
            # save empty answer for skipped questions
            st.session_state.answers.append("(Skipped)")
            st.session_state.current_q += 1
            st.rerun()


# ── STEP 4: RESULTS ───────────────────────────────────────────────
elif st.session_state.step == 4:
    
    st.subheader("Step 4: Your Results")
    
    # run evaluation if not done yet
    if st.session_state.final_result is None:
        
        analysis = st.session_state.analysis
        
        with st.spinner("Evaluating your answers and building study plan... (takes 1-2 minutes)"):
            
            # prepare state with all answers
            state_with_answers = {
                **analysis,
                'student_answers': st.session_state.answers,
                'feedback_list': [],
                'scores': [],
                'current_q_index': 0,
                'interview_done': True,
                'study_plan': ''
            }
            
            final = run_full_interview(state_with_answers)
            st.session_state.final_result = final
    
    final = st.session_state.final_result
    
    # overall score
    avg_score = sum(final['scores']) / len(final['scores']) if final['scores'] else 0
    
    st.metric("Average Interview Score", f"{avg_score:.1f} / 10")
    st.metric("Readiness Score", f"{final['readiness_score']} / 100")
    
    st.divider()
    
    # per question feedback
    st.markdown("### Interview Feedback")
    
    for i, (q, a, feedback) in enumerate(zip(
        final['questions_asked'],
        final['student_answers'],
        final['feedback_list']
    )):
        with st.expander(f"Q{i+1}: {q[:80]}...  |  Score: {final['scores'][i]}/10"):
            st.markdown(f"**Your answer:** {a}")
            st.divider()
            st.markdown("**Coach Feedback:**")
            st.markdown(feedback)
    
    st.divider()
    
    # study plan
    st.markdown("### Your 30-Day Study Plan")
    st.markdown(final['study_plan'])
    
    st.divider()
    
    # download PDF report
    if st.button("📄 Download Full Report (PDF)"):
        pdf_path = generate_pdf_report(
            student_name=final['student_name'],
            company=final['company'],
            role=final['role'],
            readiness_score=final['readiness_score'],
            skills_found=final['skills_found'],
            skills_missing=final['skills_missing'],
            feedback_list=final['feedback_list'],
            study_plan=final['study_plan']
        )
        
        with open(pdf_path, 'rb') as f:
            st.download_button(
                label="Click here to download",
                data=f,
                file_name=f"placement_report_{final['company']}.pdf",
                mime='application/pdf'
            )
    
    if st.button("🔄 Start New Session"):
        # clear everything and restart
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()