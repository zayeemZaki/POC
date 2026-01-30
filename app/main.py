import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.database import Claim, create_db_and_tables, engine
from app.agents.clinical import clinical_agent

app = FastAPI(title="Insurance Claim Agent POC")

# Allow the Next.js frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

    # Check if DB is empty
    with Session(engine) as session:
        existing_claim = session.exec(select(Claim)).first()

        if not existing_claim:
            print("Database is empty. Starting Auto-Ingestion...")
            try:
                subprocess.run(["python", "scripts/ingest.py"], check=True)
                print("Auto-Ingestion Complete.")
            except Exception as e:
                print(f"Auto-Ingestion Failed: {e}")
        else:
            print("Database already has data. Skipping ingestion.")

@app.get("/")
def read_root():
    return {"status": "System Online", "message": "Agents are ready."}

@app.get("/claims")
def get_all_claims():
    """Return all claims."""
    with Session(engine) as session:
        statement = select(Claim)
        claims = session.exec(statement).all()
        return claims

@app.get("/claims/{claim_id}")
def get_claim(claim_id: int):
    """Return a single claim by ID."""
    with Session(engine) as session:
        claim = session.get(Claim, claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim

@app.post("/verify/{claim_id}")
def run_verification(claim_id: int):
    """
    Triggers the Clinical Agent to audit a specific claim.
    """
    try:
        # Run the agent pipeline (returns a dict with coding_flags included)
        result = clinical_agent.verify_claim(claim_id)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
