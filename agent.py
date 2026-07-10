# agent.py

from groq import Groq
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from dotenv import load_dotenv
import os

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


class State(TypedDict):
    resume_text: str
    company: str
    role: str
    student_name: str
    plan_days: int          # NEW: 20, 30, 45, or 60 days
    skills_found: List[str]
    skills_missing: List[str]
    questions: List[str]
    question_sources: List[str]   # NEW: source per question
    readiness_score: int
    gap_summary: str
    questions_asked: List[str]
    student_answers: List[str]
    feedback_list: List[str]
    scores: List[int]
    current_q_index: int
    interview_done: bool
    study_plan: str


def call_llm(system_msg, user_msg):
    res = groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.3,
        max_tokens=1200
    )
    return res.choices[0].message.content


def agent1_analyzer(state: State) -> State:
    print("\nAgent 1: Analyzing...")

    # Step 1: extract skills from resume
    skills_raw = call_llm(
        "Extract technical skills from resume. Return comma separated list only. No explanation. No bullet points.",
        f"Resume:\n{state['resume_text'][:2500]}"
    )
    skills_found = [s.strip() for s in skills_raw.split(',') if s.strip()]

    # Step 2: get questions from RAG
    from rag import get_questions
    questions, sources = get_questions(state['company'], state['role'], n=12)
    questions_text = '\n'.join([f"{i+1}. {q}" for i, q in enumerate(questions)])

    # Step 3: define what this role actually needs
    # this is the key fix - we tell the LLM what the role requires
    # not just ask it to compare blindly
    # hardcoded role requirements
    # much more reliable than asking LLM
    # LLM tends to hallucinate generic CS skills like C++, MATLAB, HTML
    ROLE_SKILLS = {
        "llm engineer": "RAG Systems, LangChain, LlamaIndex, LangGraph, Vector Databases, ChromaDB, Pinecone, FAISS, Prompt Engineering, Fine-tuning, LoRA, QLoRA, PEFT, Hugging Face, Transformers, LLaMA, Mistral, Groq API, LLM Evaluation, RAGAS, LangSmith, Embeddings, Semantic Search, FastAPI, Docker",
        "agentic ai engineer": "LangGraph, AI Agents, Tool Calling, ReAct Pattern, Multi-Agent Systems, CrewAI, AutoGen, RAG Systems, Vector Databases, LangChain, LLMs, Prompt Engineering, FastAPI, Docker, LangSmith, Groq API, Hugging Face",
        "ai engineer": "Machine Learning, Deep Learning, PyTorch, Scikit-learn, RAG Systems, LangChain, Vector Databases, Prompt Engineering, Transformers, Hugging Face, Fine-tuning, LLMs, FastAPI, Docker, MLflow, SQL, Python",
        "backend engineer": "System Design, Distributed Systems, REST APIs, Microservices, SQL, PostgreSQL, Redis, Docker, Kubernetes, AWS, Message Queues, Load Balancing, Caching, Rate Limiting, FastAPI or Django or Spring Boot",
        "data scientist": "Machine Learning, Statistics, Python, Pandas, NumPy, Scikit-learn, Deep Learning, PyTorch, SQL, Data Visualization, Feature Engineering, Model Evaluation, A/B Testing, MLflow",
        "ml engineer": "Machine Learning, Deep Learning, PyTorch, TensorFlow, MLOps, MLflow, Docker, FastAPI, Feature Engineering, Model Deployment, SQL, Scikit-learn, Data Pipelines, AWS SageMaker or Azure ML",
    }

    # find matching role requirements
    role_lower = state['role'].lower()
    role_requirements = ""
    for key in ROLE_SKILLS:
        if key in role_lower:
            role_requirements = ROLE_SKILLS[key]
            break

    # if role not in our map, ask LLM but with strict constraints
    if not role_requirements:
        role_requirements = call_llm(
            """List ONLY practical technical skills for this role.
            Do NOT include: HTML, CSS, C++, MATLAB, R, Julia, Assembly, Fortran.
            Focus on: frameworks, libraries, tools, and concepts actually used day to day.
            Return comma separated list only. Maximum 15 skills.""",
            f"What are the essential practical technical skills for a {state['role']} role? No academic or rarely-used skills."
        )

    # Step 4: now compare properly
    gap_response = call_llm(
        """You are a strict placement counselor doing a skill gap analysis.
        You will be given:
        1. What the student currently has
        2. What the role actually requires

        Your job: find the GAP — what is required but NOT in the student's skills.
        Even if the student has good skills in other areas, if those skills are not relevant to this role, they are missing.

        Reply in EXACTLY this format, no extra text:
        MISSING: skill1, skill2, skill3, skill4, skill5
        SCORE: (number from 0 to 100 based on how ready they are for this specific role)
        SUMMARY: (one honest sentence about their readiness for this specific role)

        Rules:
        - MISSING must have at least 3-8 skills if the person is not from this domain
        - SCORE must be low (under 30) if the person has no relevant domain experience
        - Be honest and strict, not encouraging""",

        f"""TARGET ROLE: {state['role']} at {state['company']}

        SKILLS THIS ROLE REQUIRES:
        {role_requirements}

        SKILLS THE STUDENT CURRENTLY HAS:
        {', '.join(skills_found)}

        Find what is MISSING from the student's profile for this specific role.
        If student is a video editor applying for AI Engineer — most AI skills are missing.
        If student is a backend engineer applying for LLM Engineer — RAG, LangGraph, LLMs, fine-tuning are missing."""
    )

    # Step 5: parse response
    missing, score, summary = [], 50, ""
    import re

    for line in gap_response.split('\n'):
        line = line.strip()
        if line.startswith('MISSING:'):
            missing_text = line.replace('MISSING:', '').strip()
            missing = [s.strip() for s in missing_text.split(',') if s.strip()]
        elif line.startswith('SCORE:'):
            nums = re.findall(r'\d+', line)
            if nums:
                score = min(int(nums[0]), 100)
        elif line.startswith('SUMMARY:'):
            summary = line.replace('SUMMARY:', '').strip()

    # safety check — if LLM still returned empty missing list
    # force it to generate one
    if len(missing) == 0:
        print("Missing skills empty — forcing re-generation...")
        force_response = call_llm(
            "List technical skills this person is missing for the target role. Return comma separated list only.",
            f"""Person has these skills: {', '.join(skills_found)}
            They are applying for: {state['role']} at {state['company']}
            Role requires: {role_requirements}
            List 5-8 specific skills they are MISSING for this role."""
        )
        missing = [s.strip() for s in force_response.split(',') if s.strip()]

    # if score is suspiciously high for someone with no domain skills
    # check if their skills overlap with role requirements
    skills_lower = [s.lower() for s in skills_found]
    req_lower = role_requirements.lower()
    ai_keywords = ['llm', 'rag', 'langchain', 'langgraph', 'machine learning',
                   'deep learning', 'nlp', 'transformer', 'vector', 'embedding',
                   'fine-tun', 'neural', 'pytorch', 'tensorflow', 'hugging face']
    has_ai_skills = any(kw in ' '.join(skills_lower) for kw in ai_keywords)

    if 'ai engineer' in state['role'].lower() or 'llm' in state['role'].lower():
        if not has_ai_skills and score > 35:
            score = max(15, score - 40)  # reduce score if no AI skills

    print(f"Agent 1 done. Score: {score}/100. Missing: {missing[:3]}")

    return {
        **state,
        'skills_found': skills_found,
        'skills_missing': missing,
        'questions': questions,
        'question_sources': sources,
        'readiness_score': score,
        'gap_summary': summary,
        'questions_asked': [],
        'student_answers': [],
        'feedback_list': [],
        'scores': [],
        'current_q_index': 0,
        'interview_done': False,
        'study_plan': ''
    }

def agent2_interviewer(state: State) -> State:
    idx = state['current_q_index']
    if idx >= len(state['questions']):
        return {**state, 'interview_done': True}
    current_q = state['questions'][idx]
    asked = state['questions_asked'] + [current_q]
    print(f"Agent 2: Q{idx+1}: {current_q[:50]}...")
    return {**state, 'questions_asked': asked}


def agent3_coach(state: State) -> State:
    idx = state['current_q_index']
    if idx >= len(state['student_answers']):
        return state

    current_q = state['questions_asked'][idx]
    current_a = state['student_answers'][idx]

    print(f"Agent 3: Evaluating Q{idx+1}...")

    feedback_raw = call_llm(
        """You are a strict but helpful interview coach.
        Reply in this exact format:
        SCORE: (0-10)
        GOOD: (one sentence what was good)
        MISSING: (one sentence what was missing)
        IDEAL: (two sentences what a perfect answer includes)""",
        f"""Question: {current_q}
        Student answer: {current_a}
        Role: {state['role']} at {state['company']}"""
    )

    import re
    score = 5
    for line in feedback_raw.split('\n'):
        if line.strip().startswith('SCORE:'):
            nums = re.findall(r'\d+', line)
            if nums:
                score = min(int(nums[0]), 10)

    return {
        **state,
        'feedback_list': state['feedback_list'] + [feedback_raw],
        'scores': state['scores'] + [score],
        'current_q_index': idx + 1
    }


def agent4_planner(state: State) -> State:
    print("Agent 4: Building study plan...")

    missing = ', '.join(state['skills_missing'])
    avg = sum(state['scores']) / len(state['scores']) if state['scores'] else 0
    days = state.get('plan_days', 30)

    plan = call_llm(
        f"You are a placement prep expert. Create a realistic {days}-day study plan.",
        f"""Student: {state['student_name']}
        Target: {state['company']} — {state['role']}
        Readiness: {state['readiness_score']}/100
        Missing Skills: {missing}
        Avg Interview Score: {avg:.1f}/10
        Plan Duration: {days} days

        Create a week-by-week {days}-day plan.
        Be specific. Focus on missing skills.
        Include what to study and where."""
    )

    return {**state, 'study_plan': plan}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("analyzer", agent1_analyzer)
    graph.add_node("interviewer", agent2_interviewer)
    graph.add_node("coach", agent3_coach)
    graph.add_node("planner", agent4_planner)
    graph.set_entry_point("analyzer")
    graph.add_edge("analyzer", "interviewer")
    graph.add_edge("interviewer", "coach")

    def check_done(state: State):
        if state['interview_done'] or state['current_q_index'] >= len(state['questions']):
            return "planner"
        return "interviewer"

    graph.add_conditional_edges("coach", check_done, {
        "planner": "planner",
        "interviewer": "interviewer"
    })
    graph.add_edge("planner", END)
    return graph.compile()


placement_graph = build_graph()


def run_analysis(resume_text, company, role, student_name, plan_days=30):
    state = {
        'resume_text': resume_text,
        'company': company,
        'role': role,
        'student_name': student_name,
        'plan_days': plan_days,
        'skills_found': [],
        'skills_missing': [],
        'questions': [],
        'question_sources': [],
        'readiness_score': 0,
        'gap_summary': '',
        'questions_asked': [],
        'student_answers': [],
        'feedback_list': [],
        'scores': [],
        'current_q_index': 0,
        'interview_done': False,
        'study_plan': ''
    }
    return agent1_analyzer(state)


def run_evaluation(state_with_answers):
    temp = state_with_answers.copy()
    for i in range(len(temp['student_answers'])):
        temp['current_q_index'] = i
        temp = agent3_coach(temp)
    temp = agent4_planner(temp)
    return temp