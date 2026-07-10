# rag.py

import json
import chromadb
from sentence_transformers import SentenceTransformer

print("Loading embedding model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding model ready.")

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="questions",
    metadata={"hnsw:space": "cosine"}
)


def build_question_bank():
    if collection.count() > 0:
        print(f"Question bank ready: {collection.count()} questions.")
        return

    with open('questions.json', 'r') as f:
        questions = json.load(f)

    print(f"Building question bank with {len(questions)} questions...")

    ids, embeddings, documents, metadatas = [], [], [], []

    for i, q in enumerate(questions):
        text = f"{q['company']} {q['role']} {q['question']} {' '.join(q['topics'])}"
        embedding = embedder.encode(text).tolist()
        ids.append(f"q{i}")
        embeddings.append(embedding)
        documents.append(q['question'])
        metadatas.append({
            "company": q['company'],
            "role": q['role'],
            "difficulty": q['difficulty'],
            "topics": ', '.join(q['topics']),
            "source": "PrepSensei Database"
        })

    collection.add(ids=ids, embeddings=embeddings,
                   documents=documents, metadatas=metadatas)
    print(f"Done. {collection.count()} questions stored.")


def get_questions(company, role, n=12):
    # returns questions AND their sources
    query = f"{company} {role} interview questions"
    query_embedding = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n,
        where={"company": {"$in": [company, "Generic"]}},
        include=['documents', 'metadatas']
    )

    questions = results['documents'][0]
    sources = ["PrepSensei Database"] * len(questions)

    # web fallback if not enough local questions
    if len(questions) < 5:
        print(f"Only {len(questions)} local. Searching web...")
        web_qs, web_sources = search_web(company, role)
        questions = questions + web_qs
        sources = sources + web_sources

    return questions[:n], sources[:n]


def search_web(company, role):
    questions = []
    sources = []

    try:
        from duckduckgo_search import DDGS

        search_sites = [
            (f"{company} {role} interview questions site:glassdoor.com", "Glassdoor"),
            (f"{company} {role} interview questions site:geeksforgeeks.org", "GeeksForGeeks"),
            (f"{role} interview questions India 2024 site:interviewbit.com", "InterviewBit"),
        ]

        with DDGS() as ddgs:
            for query, site_name in search_sites:
                try:
                    results = list(ddgs.text(query, max_results=4))
                    for r in results:
                        body = r.get('body', '')
                        sentences = body.split('.')
                        for s in sentences:
                            s = s.strip()
                            if (30 < len(s) < 250 and
                                any(s.lower().startswith(w) for w in
                                    ['how', 'what', 'why', 'explain',
                                     'design', 'describe', 'implement'])):
                                questions.append(s)
                                sources.append(site_name)
                except:
                    continue

        return questions[:7], sources[:7]

    except Exception as e:
        print(f"Web search error: {e}")
        return [], []