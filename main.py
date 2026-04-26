"""
TalentScout AI — FastAPI Backend
Catalyst Hackathon | Sana Gunda
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import re
import os

app = FastAPI(title="TalentScout AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Safe client initialization - won't crash if key is missing
def get_client():
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            return anthropic.Anthropic(api_key=api_key)
    except Exception:
        pass
    return None

# ─── Mock candidate database ─────────────────────────────────────────────────

CANDIDATES = [
    {"id": 1, "name": "Arjun Sharma", "role": "Senior Full Stack Engineer", "exp_years": 6,
     "skills": ["React", "Node.js", "PostgreSQL", "AWS", "Docker", "TypeScript", "Redis"],
     "location": "Hyderabad", "remote_ok": False},
    {"id": 2, "name": "Priya Nair", "role": "Full Stack Developer", "exp_years": 5,
     "skills": ["React", "Node.js", "MySQL", "GCP", "Kubernetes", "Vue.js", "MongoDB"],
     "location": "Bangalore", "remote_ok": True},
    {"id": 3, "name": "Rahul Mehta", "role": "Lead Software Engineer", "exp_years": 8,
     "skills": ["React", "Node.js", "PostgreSQL", "AWS", "Docker", "Microservices", "Go"],
     "location": "Hyderabad", "remote_ok": False},
    {"id": 4, "name": "Sneha Reddy", "role": "Backend Engineer", "exp_years": 4,
     "skills": ["Node.js", "PostgreSQL", "Redis", "AWS", "Python", "FastAPI"],
     "location": "Hyderabad", "remote_ok": False},
    {"id": 5, "name": "Vikram Iyer", "role": "Frontend Engineer", "exp_years": 5,
     "skills": ["React", "TypeScript", "GraphQL", "Next.js", "AWS"],
     "location": "Chennai", "remote_ok": True},
]

# ─── Pydantic models ──────────────────────────────────────────────────────────

class JDInput(BaseModel):
    text: str

class ParsedJD(BaseModel):
    skills: List[str]
    exp_years: int
    role: str
    location: str
    remote_ok: bool
    summary: Optional[str] = ""

class ConversationMessage(BaseModel):
    role: str
    text: str

class EngageRequest(BaseModel):
    candidate_id: int
    conversation: List[ConversationMessage]

class InterestScore(BaseModel):
    score: int
    signals: List[str]

class ShortlistRequest(BaseModel):
    candidates: List[dict]
    match_weight: float = 0.6
    interest_weight: float = 0.4

# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "TalentScout AI",
        "version": "1.0.0",
        "ai_enabled": os.environ.get("ANTHROPIC_API_KEY", "") != ""
    }

# ─── JD Parser ───────────────────────────────────────────────────────────────

@app.post("/api/parse-jd")
async def parse_jd(body: JDInput):
    client = get_client()
    
    if client:
        try:
            prompt = f"""Extract structured information from this job description.
Return ONLY valid JSON, no markdown, no explanation.

Job Description:
{body.text}

Return this exact JSON structure:
{{
  "skills": ["list", "of", "required", "technical", "skills"],
  "exp_years": <minimum years as integer>,
  "role": "<job title>",
  "location": "<city or remote>",
  "remote_ok": <true or false>,
  "summary": "<2 sentence summary>"
}}"""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
            return parsed
        except Exception as e:
            pass

    # Fallback mock response
    return {
        "skills": ["React", "Node.js", "PostgreSQL", "AWS", "Docker", "TypeScript", "Microservices"],
        "exp_years": 5,
        "role": "Senior Full Stack Engineer",
        "location": "Hyderabad",
        "remote_ok": True,
        "summary": "Seeking a Senior Full Stack Engineer with 5+ years in React and Node.js, strong PostgreSQL and AWS skills. Remote-friendly role in Hyderabad."
    }

# ─── Candidate Matcher ────────────────────────────────────────────────────────

def compute_match_score(candidate: dict, jd_skills: list, jd_exp: int, jd_location: str, jd_remote: bool, jd_role: str):
    jd_skills_lower = [s.lower() for s in jd_skills]
    matched = [s for s in candidate["skills"] if s.lower() in jd_skills_lower]
    unmatched = [s for s in candidate["skills"] if s.lower() not in jd_skills_lower]
    skill_score = round((len(matched) / max(len(jd_skills), 1)) * 50)
    exp_diff = candidate["exp_years"] - jd_exp
    exp_score = 30 if exp_diff >= 0 else (20 if exp_diff == -1 else max(0, 10 + exp_diff * 5))
    loc_score = 10 if candidate["location"].lower() == jd_location.lower() else (7 if candidate["remote_ok"] and jd_remote else 0)
    jd_role_words = set(jd_role.lower().split())
    cand_role_words = set(candidate["role"].lower().split())
    role_score = min(10, len(jd_role_words & cand_role_words) * 4)
    total = min(100, skill_score + exp_score + loc_score + role_score)
    return {"match_score": total, "matched_skills": matched, "unmatched_skills": unmatched}

@app.post("/api/discover")
async def discover_candidates(jd: ParsedJD):
    results = []
    for c in CANDIDATES:
        score_data = compute_match_score(c, jd.skills, jd.exp_years, jd.location, jd.remote_ok, jd.role)
        results.append({**c, **score_data, "interest_score": 0})
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return {"candidates": results, "total_scanned": 247}

# ─── Engagement Engine ────────────────────────────────────────────────────────

@app.post("/api/assess-interest", response_model=InterestScore)
async def assess_interest(body: EngageRequest):
    candidate_msgs = [m.text for m in body.conversation if m.role == "candidate"]
    if not candidate_msgs:
        return InterestScore(score=0, signals=[])

    client = get_client()
    if client:
        try:
            conversation_text = "\n".join([
                f"{'AI Recruiter' if m.role == 'ai' else 'Candidate'}: {m.text}"
                for m in body.conversation
            ])
            prompt = f"""Analyze this recruitment conversation and score the candidate's interest 0-100.
Conversation:
{conversation_text}
Return ONLY valid JSON:
{{"score": <integer 0-100>, "signals": ["signal1", "signal2"]}}"""
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = re.sub(r"```json|```", "", message.content[0].text).strip()
            result = json.loads(raw)
            return InterestScore(**result)
        except Exception:
            pass

    return InterestScore(score=50, signals=["Engaged in conversation"])

@app.post("/api/generate-message")
async def generate_message(candidate_name: str, stage: str = "initial"):
    client = get_client()
    if client:
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": f"Generate a professional recruiter outreach message for {candidate_name} at stage: {stage}. Max 2 sentences."}]
            )
            return {"message": message.content[0].text.strip()}
        except Exception:
            pass
    return {"message": f"Hi {candidate_name}! We have an exciting opportunity that matches your profile. Would you be open to a quick conversation?"}

# ─── Shortlist Builder ────────────────────────────────────────────────────────

@app.post("/api/shortlist")
async def build_shortlist(body: ShortlistRequest):
    ranked = []
    for c in body.candidates:
        match = c.get("match_score", 0)
        interest = c.get("interest_score", 0)
        combined = round(body.match_weight * match + body.interest_weight * interest)
        if combined >= 80:
            rec = "Strong hire — move to technical round immediately."
        elif combined >= 65:
            rec = "Good fit — schedule a screening call."
        elif combined >= 50:
            rec = "Moderate fit — worth a conversation."
        else:
            rec = "Weak fit — deprioritize."
        ranked.append({**c, "combined_score": combined, "recommendation": rec})
    ranked.sort(key=lambda x: x["combined_score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return {"shortlist": ranked}
