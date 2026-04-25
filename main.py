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
import anthropic
import os

app = FastAPI(title="TalentScout AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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

class ConversationMessage(BaseModel):
    role: str  # "ai" | "candidate"
    text: str

class EngageRequest(BaseModel):
    candidate_id: int
    conversation: List[ConversationMessage]

class InterestScore(BaseModel):
    score: int
    signals: List[str]

# ─── JD Parser ───────────────────────────────────────────────────────────────

@app.post("/api/parse-jd", response_model=ParsedJD)
async def parse_jd(body: JDInput):
    """Use Claude to extract structured requirements from a raw JD."""
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
  "remote_ok": <true or false>
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = message.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    
    try:
        parsed = json.loads(raw)
        return ParsedJD(**parsed)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parse error: {e}")


# ─── Candidate Matcher ────────────────────────────────────────────────────────

def compute_match_score(candidate: dict, jd: ParsedJD) -> dict:
    """Compute match score with explainability."""
    jd_skills_lower = [s.lower() for s in jd.skills]
    cand_skills_lower = [s.lower() for s in candidate["skills"]]
    
    matched = [s for s in candidate["skills"] if s.lower() in jd_skills_lower]
    skill_score = round((len(matched) / max(len(jd.skills), 1)) * 50)
    
    exp_diff = candidate["exp_years"] - jd.exp_years
    if exp_diff >= 0:
        exp_score = 30
    elif exp_diff == -1:
        exp_score = 20
    else:
        exp_score = max(0, 10 + exp_diff * 5)
    
    jd_loc = jd.location.lower()
    cand_loc = candidate["location"].lower()
    if cand_loc in jd_loc or jd_loc in cand_loc:
        loc_score = 10
    elif candidate["remote_ok"] and jd.remote_ok:
        loc_score = 7
    else:
        loc_score = 0
    
    # Role alignment (simple keyword check)
    jd_role_words = set(jd.role.lower().split())
    cand_role_words = set(candidate["role"].lower().split())
    overlap = jd_role_words & cand_role_words
    role_score = min(10, len(overlap) * 3)
    
    total = min(100, skill_score + exp_score + loc_score + role_score)
    
    return {
        "match_score": total,
        "matched_skills": matched,
        "explanation": {
            "skill_score": skill_score,
            "exp_score": exp_score,
            "loc_score": loc_score,
            "role_score": role_score,
            "skills_matched": f"{len(matched)}/{len(jd.skills)}",
        }
    }


@app.post("/api/discover")
async def discover_candidates(jd: ParsedJD):
    """Score all candidates against the parsed JD."""
    results = []
    for c in CANDIDATES:
        score_data = compute_match_score(c, jd)
        results.append({
            **c,
            **score_data,
            "interest_score": 0,
            "combined_score": score_data["match_score"]
        })
    
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return {"candidates": results, "total_scanned": 247}


# ─── Engagement Engine ────────────────────────────────────────────────────────

@app.post("/api/assess-interest", response_model=InterestScore)
async def assess_interest(body: EngageRequest):
    """Analyze a conversation to produce an interest score."""
    candidate_msgs = [m.text for m in body.conversation if m.role == "candidate"]
    
    if not candidate_msgs:
        return InterestScore(score=0, signals=[])
    
    conversation_text = "\n".join([
        f"{'AI Recruiter' if m.role == 'ai' else 'Candidate'}: {m.text}"
        for m in body.conversation
    ])
    
    prompt = f"""Analyze this recruitment conversation and score the candidate's genuine interest in the job opportunity.

Conversation:
{conversation_text}

Score the candidate's interest from 0-100 based on:
- Enthusiasm and positive language (+)
- Questions showing engagement (+)
- Sharing personal details like comp expectations / notice period (+)
- Requesting next steps (+)
- Hedging, vagueness, or disinterest (-)

Return ONLY valid JSON:
{{
  "score": <integer 0-100>,
  "signals": ["list of specific observed signals, max 4"]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = message.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    
    try:
        result = json.loads(raw)
        return InterestScore(**result)
    except Exception:
        return InterestScore(score=50, signals=["Unable to parse interest signals"])


@app.post("/api/generate-message")
async def generate_outreach_message(
    candidate_name: str,
    conversation: List[ConversationMessage],
    stage: str = "initial"
):
    """Generate the next AI recruiter message in the conversation."""
    history = "\n".join([
        f"{'AI' if m.role == 'ai' else 'Candidate'}: {m.text}"
        for m in conversation
    ])
    
    prompt = f"""You are a warm, professional AI recruiter engaging with {candidate_name}.
Current conversation stage: {stage}

Conversation so far:
{history if history else "This is the opening message."}

Generate the next recruiter message. Be natural, conversational, and professional.
Ask ONE focused question to assess interest or gather information.
Keep it under 3 sentences.

Return ONLY the message text, no labels, no quotes."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"message": message.content[0].text.strip()}


# ─── Shortlist Builder ────────────────────────────────────────────────────────

class ShortlistRequest(BaseModel):
    candidates: List[dict]
    match_weight: float = 0.6
    interest_weight: float = 0.4

@app.post("/api/shortlist")
async def build_shortlist(body: ShortlistRequest):
    """Compute final ranked shortlist combining match and interest scores."""
    ranked = []
    for c in body.candidates:
        match = c.get("match_score", 0)
        interest = c.get("interest_score", 0)
        combined = round(body.match_weight * match + body.interest_weight * interest)
        
        if combined >= 80:
            recommendation = "Strong hire — move to technical round immediately."
        elif combined >= 65:
            recommendation = "Good fit — schedule a screening call."
        elif combined >= 50:
            recommendation = "Moderate fit — explore if pipeline is thin."
        else:
            recommendation = "Weak fit — deprioritize unless no stronger options."
        
        ranked.append({**c, "combined_score": combined, "recommendation": recommendation})
    
    ranked.sort(key=lambda x: x["combined_score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    
    return {"shortlist": ranked}


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "TalentScout AI", "version": "1.0.0"}
