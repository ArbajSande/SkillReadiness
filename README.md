# SkillReadiness AI

SkillReadiness AI is an intelligent talent intelligence and career engineering platform that bridges the gap between candidate qualifications and target industry benchmarks through interactive adaptive assessments, readiness gap analytics, and prerequisite-aware learning paths.

---

## Architecture & Technology Stack

- **Backend:** FastAPI (Python 3.12), Motor (Async MongoDB), Pydantic v2, Pytest, PyPDF, Python-docx, JWT Security, Bcrypt
- **Frontend:** React 19, Vite, Tailwind CSS, Lucide Icons, ESLint
- **Database:** MongoDB (`mongodb://localhost:27017`), Database: `skill_readiness_db`
- **Assessment Engine:** Interactive item-level adaptive testing (`ADAPT-v1.0-baseline`) with anti-tampering verification and dynamic difficulty stepping (Beginner ↔ Intermediate ↔ Advanced)
- **Readiness Engine:** Versioned scoring formula (`SR-v2.0-baseline`) segregating **Critical Core Gaps** from **Elective Specialization Gaps**, with chronological historical snapshot persistence
- **Curriculum Engine:** Directed Acyclic Graph (DAG) topological scheduling for prerequisite-ordered learning path generation

---

## Quick Start Guide

### 1. Prerequisites
- **Node.js:** v18+ (tested on v22.19.0)
- **Python:** 3.10+ (tested on 3.12.3)
- **MongoDB:** Running instance on `mongodb://localhost:27017`

### 2. Backend Setup & Run

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server (Runs on http://127.0.0.1:8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Documentation:** http://127.0.0.1:8000/docs
- **Health Check Endpoint:** http://127.0.0.1:8000/health

### 3. Frontend Setup & Run

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run Development Server (Runs on http://127.0.0.1:5173)
npm run dev

# Run Production Build
npm run build

# Run Code Quality Lint
npm run lint
```

---

## Verification & Research Evaluation

### 1. Backend Test Suite (Pytest)
```bash
cd backend
python -m pytest tests -v
```
*Covers 24 tests across adaptive question selection, anti-tampering, session resumption, readiness scoring edge cases, rate limiting, oversized file rejection, DAG cycle detection, and multi-tenant security isolation.*

### 2. Research Baseline Evaluation Benchmark
```bash
python evaluation/evaluate_baseline.py
```
*Evaluates extraction precision/recall/F1, skill-gap identification accuracy, readiness score bounds, and learning-path prerequisite ordering on labeled synthetic benchmarks.*

### 3. Live End-to-End Integration Verification
```bash
# Ensure backend and MongoDB are running, then run from root:
python verify_end_to_end.py
```
*Exercises all 9 steps: User Registration -> Login -> Resume Upload -> Adaptive Assessment -> Readiness Calculation -> History Persistence -> Learning Path Generation -> Progress Persistence -> Assessment Competency Decoupling.*

---

## Environment Configuration (`backend/.env.example`)

```env
MONGODB_URL=mongodb://localhost:27017
DB_NAME=skill_readiness_db
SECRET_KEY=skillreadiness_production_super_secret_key_2026_jwt_token_sign
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```
