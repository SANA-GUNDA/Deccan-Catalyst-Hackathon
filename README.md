# TalentScout AI — Catalyst Hackathon Submission

> AI-Powered Talent Scouting & Engagement Agent  
> Built for Catalyst by Deccan AI | Submitted by Sana Gunda

---

## Overview

TalentScout AI is a full-stack AI agent that transforms a raw Job Description into a ranked, actionable candidate shortlist — completely autonomously. It parses JDs, discovers matching candidates via semantic skill matching, engages them through simulated conversational outreach with real-time interest scoring, and outputs a two-dimensional ranked shortlist (Match Score + Interest Score).

## Live Demo

> [Insert deployed URL here]

## Demo Video

> [Insert Loom/YouTube link here — 3–5 min walkthrough]

---

## Features

| Feature | Description |
|---|---|
| JD Parsing | Extracts skills, experience, location, role type from raw text |
| Candidate Discovery | Scans 247+ profiles, ranks top matches with explainability |
| Conversational Outreach | Simulated AI-driven chat to assess genuine interest |
| Interest Scoring | Real-time NLP-based interest signal detection |
| Ranked Shortlist | Two-axis scoring: Match Score + Interest Score → Combined |
| Explainability | Per-candidate reasoning for every score |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Recruiter UI                      │
│   (React SPA — 4 tabs: Parse → Discover → Engage → Shortlist) │
└───────────────────┬─────────────────────────────────┘
                    │ REST API
┌───────────────────▼─────────────────────────────────┐
│                 FastAPI Backend                     │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  JD Parser  │  │  Candidate  │  │  Engagement │ │
│  │  Module     │  │  Matcher    │  │  Engine     │ │
│  │             │  │             │  │             │ │
│  │ • Skill     │  │ • Semantic  │  │ • Chat sim  │ │
│  │   extract   │  │   matching  │  │ • Interest  │ │
│  │ • Exp parse │  │ • Scoring   │  │   scoring   │ │
│  │ • Location  │  │ • Ranking   │  │ • NLP clasf │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         └────────────────┼────────────────┘        │
│                          │                          │
│  ┌───────────────────────▼───────────────────────┐  │
│  │              Scoring Engine                   │  │
│  │   Combined = 0.6×Match + 0.4×Interest         │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                    │
        ┌───────────▼──────────┐
        │   Claude API         │
        │   (Anthropic)        │
        │   claude-sonnet-4    │
        └──────────────────────┘
```

---

## Scoring Logic

### Match Score (60% weight)
Computed via weighted keyword extraction and semantic matching:
- **Skill overlap**: Required skills from JD vs candidate skills → `matched/total × 50`
- **Experience**: Years of experience vs JD requirement → `0-30 points`
- **Location**: Exact match = 10pts, remote-ok = 7pts, mismatch = 0
- **Role alignment**: Semantic similarity of job titles → `0-10 points`

### Interest Score (40% weight)
Derived from conversational signals during AI-driven outreach:
- **Explicit enthusiasm** ("I'm very excited", "sounds great") → +35 pts
- **Questions asked** (deeper engagement signal) → +20 pts per relevant question
- **Salary engagement** (sharing current comp, asking about range) → +15 pts
- **Availability stated** (notice period, timeline) → +25 pts
- **Hedging language** ("maybe", "I'll think about it") → negative signal

### Combined Score
```
Combined = (0.6 × MatchScore) + (0.4 × InterestScore)
```
Normalized to 0–100. Candidates without engagement default to Match Score only.

---

## Tech Stack

**Frontend**
- React 18 + Vite
- TailwindCSS
- Recharts (scoring visualization)

**Backend**
- FastAPI (Python 3.11)
- Claude API (claude-sonnet-4) for JD parsing and interest classification
- spaCy for NLP preprocessing
- SQLite (candidate profiles mock DB)

**Infrastructure**
- Vercel (frontend)
- Railway (backend)

---

## Local Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Anthropic API key

### Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn main:app --reload
# API at http://localhost:8000
```

---

## Sample Inputs & Outputs

### Input: Job Description
```
Senior Full Stack Engineer — TechVentures Hyderabad

5+ years of hands-on experience required.
Expert-level React.js and Node.js.
Strong PostgreSQL skills.
AWS (EC2, S3, Lambda, RDS) experience.
Docker and microservices architecture.
Location: Hyderabad (Remote-friendly)
```

### Output: Ranked Shortlist
```json
{
  "shortlist": [
    {
      "rank": 1,
      "name": "Arjun Sharma",
      "role": "Senior Full Stack Engineer",
      "match_score": 92,
      "interest_score": 100,
      "combined_score": 95,
      "matched_skills": ["React", "Node.js", "PostgreSQL", "AWS", "Docker"],
      "interest_signals": ["expressed enthusiasm", "asked about tech stack", "shared compensation expectations", "stated availability"],
      "recommendation": "Strong hire — high match AND high interest. Move to technical round immediately."
    },
    {
      "rank": 2,
      "name": "Rahul Mehta",
      "role": "Lead Software Engineer",
      "match_score": 88,
      "interest_score": 100,
      "combined_score": 93,
      "matched_skills": ["React", "Node.js", "PostgreSQL", "AWS", "Docker"],
      "interest_signals": ["asked about architecture ownership", "excited about Go roadmap", "requested immediate call"],
      "recommendation": "Strong hire — leadership experience and very high engagement."
    },
    {
      "rank": 3,
      "name": "Priya Nair",
      "match_score": 78,
      "interest_score": 35,
      "combined_score": 61,
      "recommendation": "Moderate fit. Passively interested — may need stronger pitch or comp offer."
    }
  ],
  "metadata": {
    "profiles_scanned": 247,
    "time_to_shortlist": "2.3s",
    "jd_skills_extracted": 7
  }
}
```

---

## Repository Structure

```
talentscout-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── JDParser.jsx
│   │   │   ├── CandidateDiscovery.jsx
│   │   │   ├── EngagementChat.jsx
│   │   │   └── Shortlist.jsx
│   │   ├── hooks/
│   │   │   └── useScoring.js
│   │   └── App.jsx
│   └── package.json
├── backend/
│   ├── main.py
│   ├── modules/
│   │   ├── jd_parser.py
│   │   ├── candidate_matcher.py
│   │   ├── engagement_engine.py
│   │   └── scoring.py
│   ├── data/
│   │   └── candidates.json
│   └── requirements.txt
├── architecture-diagram.png
└── README.md
```

---

## Team

**Sana Gunda** — Solo submission  
Built for Catalyst by Deccan AI

---

## License
MIT
