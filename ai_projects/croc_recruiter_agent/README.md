# LLM Application Engineer — Technical Assessment

## Overview

You are building a **Conversational BI Assistant** for an internal staffing operations team. The assistant allows business analysts to query staffing data (jobs, candidates, placements) in natural language and consult internal policy documents — all while respecting user-level access permissions.

**Time expectation:** 3–4 hours of focused work. You have **72 hours** from receiving this repo to submit your solution.

---

## Context

Your company operates across multiple US regions and divisions. Analysts need quick answers to questions like:

- *"How many open jobs do we have in the Southeast region?"*
- *"What's the average bill rate for IT placements in Q4 2025?"*
- *"What does our onboarding SOP say about background checks?"*
- *"Show me the top 5 candidates placed in the West Coast last month."*

Different analysts have access to different regions and divisions based on their role. The system must enforce this at the data layer — **not as a UI filter that can be bypassed**.

---

## What You're Building

A conversational agent (CLI or simple web UI) that supports four core capabilities:

### 1. Structured Data Querying (Text-to-SQL)

- The agent must interpret natural language questions and translate them into SQL queries against the provided SQLite database (`data/staffing.db`).
- Queries should be validated before execution (prevent injection, limit scope to read-only).
- Results should be returned in a user-friendly format.

**Example interaction:**
```
User (region: Southeast): "How many placements did we close this quarter?"
Agent: Based on your region access, there were 47 placements closed in 
       the Southeast region in Q1 2026.
```

### 2. RAG over Internal Documents

- Ingest the markdown documents in `data/documents/` into a vector store.
- Implement retrieval-augmented generation so the agent can answer questions grounded in these documents.
- The agent should cite which document informed its answer.

**Example interaction:**
```
User: "What's the company policy on contractor time-off requests?"
Agent: According to the Contractor Policies document, contractors must submit 
       time-off requests at least 5 business days in advance through the VMS 
       portal. [Source: policy_contractor.md]
```

### 3. Row-Level Security (RLS)

- Each user has a profile defined in `data/user_permissions.json` specifying which **regions** and **divisions** they can access.
- The agent MUST filter all structured data queries based on the authenticated user's permissions.
- Security filtering must happen **before data reaches the LLM** — the model should never see data the user isn't authorized to access.
- Document access is unrestricted (all policies are company-wide).

**How to handle user identity:** Your application should accept a `--user` flag (CLI) or login selector (web UI) that loads the user's permission profile. No real auth is needed — we want to see your RLS implementation logic.

### 4. Semantic Cache

- Implement a caching layer that detects **semantically similar** questions and returns cached responses without making a new LLM call.
- Define a similarity threshold and explain your choice.
- Handle cache invalidation — at minimum, support a TTL-based expiration.
- The cache should be **user-aware**: cached responses for one user's permission scope should NOT be served to a user with different permissions.

**Example:**
```
# First call — hits LLM
User A (region: Southeast): "How many open jobs are there?"
→ LLM call → "There are 23 open jobs in the Southeast region."

# Second call — served from cache (same user, similar question)
User A: "What's the count of open positions?"  
→ Cache hit (similarity: 0.94) → "There are 23 open jobs in the Southeast region."

# Third call — NOT served from cache (different user permissions)
User B (region: West Coast): "How many open jobs are there?"
→ LLM call → "There are 31 open jobs in the West Coast region."
```

---

## Repository Structure

```
├── README.md                    ← You are here
├── ARCHITECTURE_TEMPLATE.md     ← Fill this out (required)
├── data/
│   ├── seed_database.py         ← Script that generates staffing.db
│   ├── staffing.db              ← SQLite database (pre-generated)
│   ├── user_permissions.json    ← User access profiles
│   └── documents/               ← Internal docs for RAG
│       ├── sop_onboarding.md
│       ├── sop_timesheet.md
│       ├── policy_contractor.md
│       ├── policy_data_privacy.md
│       └── faq_benefits.md
├── src/                         ← Your code goes here
├── docker-compose.yml           ← Template (modify as needed)
├── requirements.txt             ← Base dependencies (extend as needed)
└── .gitignore
```

---

## Deliverables

1. **Working application** in `src/` that implements all four capabilities.
2. **ARCHITECTURE_TEMPLATE.md** filled out with your design decisions and Azure migration plan.
3. **Updated `docker-compose.yml`** so we can run your solution with `docker compose up`.
4. **Brief demo video** (5 min max, Loom or similar) walking through your solution and key decisions.

---

## Technical Constraints

- **Language:** Python (3.10+)
- **LLM:** Use any provider you have access to (OpenAI, Anthropic, local via Ollama, etc.). Document which model you chose and why.
- **Vector Store:** Your choice (ChromaDB, FAISS, Qdrant, etc.)
- **Framework:** Your choice (LangChain, LlamaIndex, Semantic Kernel, raw SDK, etc.) or no framework at all. This is a signal — choose intentionally.
- **Database:** Use the provided SQLite database as-is. Do not modify the schema.

---

## Evaluation Criteria

| Criteria                          | Weight |
|-----------------------------------|--------|
| Functionality (all 4 capabilities work)| 30%  |
| Architecture & Code Quality       | 25%    |
| Security / RLS Implementation     | 20%    |
| Semantic Cache Design             | 15%    |
| Documentation & Communication     | 10%    |

---

## Rules & Expectations

- **You may use any tools**, including LLMs, Copilot, documentation, etc. Please list what you used and for what purpose in your ARCHITECTURE_TEMPLATE.md.
- **What we're evaluating** is whether you understand what you built, can explain your trade-offs, and can extend your solution under pressure. The live session will test this.
- **Do not over-engineer.** A clean, well-documented solution that works for the core cases is better than a complex one that's fragile.
- **Ask questions.** If something in the requirements is ambiguous, document your interpretation and move forward. Showing good judgment under ambiguity is a plus.

---

## After Submission

You will be invited to a **45–60 minute live session** where you will:

1. **Present** your solution and explain your design decisions (15 min).
2. **Extend** the solution with a new requirement we'll give you on the spot (20–25 min).
3. **Discuss** how you'd migrate this to a production Azure environment (10–15 min).

---

## Setup

```bash
# Clone the repo
git clone <your-assigned-repo-url>
cd llm-engineer-assessment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install base dependencies
pip install -r requirements.txt

# Verify database
python -c "import sqlite3; conn = sqlite3.connect('data/staffing.db'); print(conn.execute('SELECT COUNT(*) FROM jobs').fetchone())"

# Run the seed script if you need to regenerate the database
python data/seed_database.py
```

Good luck. Build something you'd be proud to deploy.
