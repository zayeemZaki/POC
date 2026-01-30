import sys
import os
import pandas as pd
import vecs
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select

# Add parent dir to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Claim, create_db_and_tables, engine

CSV_PATH = "data/poc_dataset.csv"

MOCK_POLICIES = [
    {
        "policy_id": "LCD-33722",
        "title": "Surgical Treatment of Peyronie's Disease",
        "text": """
        POLICY LCD-33722: PENILE PROSTHESIS REPLACEMENT

        Indications:
        Replacement of an inflatable penile prosthesis is covered if the device malfunctions.

        Coding Guidelines:
        - Modifier -22 (Increased Procedural Services) may be reported if the procedure required significant additional time/effort due to dense scarring (fibrosis).
        - Documentation must clearly state the time duration and the nature of the difficulty (e.g., "required 45 mins of dissection due to calcification").
        - If Modifier -22 is missing despite documentation of complex lysis of adhesions, the claim may be denied for inconsistency.
        """
    },
    {
        "policy_id": "LCD-32849",
        "title": "Non-Invasive Vascular Testing",
        "text": """
        POLICY LCD-32849: CEREBROVASCULAR EVALUATION

        Medical Necessity:
        - Covered for patients with transient ischemic attacks (TIA) or amaurosis fugax.
        - Symptoms must be transient and focal.

        Documentation Requirements:
        - Provider must document specific visual symptoms (e.g., "curtain coming down").
        - General "dizziness" without focal neuro signs is NOT sufficient for coverage.
        """
    },
    {
        "policy_id": "POL-8253",
        "title": "Emergency Care for Insect Stings",
        "text": """
        POLICY POL-8253: CIGNA EMERGENCY GUIDELINES

        Medical Necessity for Emergency Visits (Level 3/4):
        - Simple insect stings (bee, wasp) with LOCAL reaction only (redness, swelling < 10cm) are considered minor and do not justify high-level emergency codes.
        - Systemic symptoms (shortness of breath, tongue swelling, hypotension) MUST be present to justify higher acuity billing.
        - If only local care (ice, antihistamine) is provided, the claim may be downcoded or denied as not medically necessary.
        """
    }
]

def ingest_data():
    print("Starting Ingestion Phase...")

    # Initialize DB tables
    create_db_and_tables()

    # Load CSV
    if not os.path.exists(CSV_PATH):
        print(f"Error: File not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    # Normalize column names to match our Model (lower case, underscores)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # ── Phase 1: SQL Data Ingestion (PostgreSQL via SQLModel) ──
    with Session(engine) as session:
        existing = session.exec(select(Claim)).first()
        if existing:
            print("Database already has data. Skipping SQL ingestion.")
        else:
            print(f"Importing {len(df)} rows into PostgreSQL...")

            def safe_str(val):
                """Convert value to string, returning None for NaN/missing."""
                if pd.isnull(val):
                    return None
                return str(val)

            def safe_float(val):
                """Convert value to float, returning None for NaN/missing."""
                if pd.isnull(val):
                    return None
                return float(val)

            for _, row in df.iterrows():
                claim = Claim(
                    patient_id=str(row.get("patient_id")),
                    description=str(row.get("description", "")),
                    medical_specialty=safe_str(row.get("medical_specialty")),
                    sample_name=safe_str(row.get("sample_name")),
                    transcription=safe_str(row.get("transcription")),
                    keywords=safe_str(row.get("keywords")),
                    cpt_code=str(row.get("cpt_code", "")),
                    cpt_description=safe_str(row.get("cpt_description")),
                    cpt_modifier=safe_str(row.get("cpt_modifier")),
                    icd_code=safe_str(row.get("icd_code")),
                    icd_description=safe_str(row.get("icd_description")),
                    bill_type=safe_str(row.get("bill_type")),
                    provider_specialty=safe_str(row.get("provider_specialty")),
                    denial_code=safe_str(row.get("denial_code")),
                    denial_reason=safe_str(row.get("denial_reason")),
                    member_id=safe_str(row.get("member_id")),
                    payer_name=safe_str(row.get("payer_name")),
                    plan_type=safe_str(row.get("plan_type")),
                    policy_id=safe_str(row.get("policy_id")),
                    claim_number=safe_str(row.get("claim_number")),
                    group_number=safe_str(row.get("group_number")),
                    provider_npi=safe_str(row.get("provider_npi")),
                    facility_name=safe_str(row.get("facility_name")),
                    place_of_service=safe_str(row.get("place_of_service")),
                    date_of_service=safe_str(row.get("date_of_service")),
                    date_of_submission=safe_str(row.get("date_of_submission")),
                    date_of_denial=safe_str(row.get("date_of_denial")),
                    prior_auth_number=safe_str(row.get("prior_auth_number")),
                    claim_amount=safe_float(row.get("claim_amount")),
                    patient_dob=safe_str(row.get("patient_dob")),
                    patient_gender=safe_str(row.get("patient_gender")),
                )
                session.add(claim)
            session.commit()
            print("SQL Data Ingested Successfully.")

    # ── Phase 2: Vector DB Ingestion (Supabase via vecs) ──
    print("Ingesting Policies into Supabase Vector Store...")

    db_url = os.getenv("DATABASE_URL", "")
    vx = vecs.create_client(db_url)

    # Get or create the collection (384 = all-MiniLM-L6-v2 dimension)
    collection = vx.get_or_create_collection(
        name="payer_policies",
        dimension=384,
    )

    # Load embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Build records: (id, vector, metadata)
    records = []
    for p in MOCK_POLICIES:
        embedding = model.encode(p["text"]).tolist()
        records.append((
            p["policy_id"],
            embedding,
            {"title": p["title"], "text": p["text"]},
        ))

    # Upsert vectors (idempotent — safe to re-run)
    collection.upsert(records=records)

    # Create / update the index for fast queries
    collection.create_index()

    print(f"Indexed {len(records)} policies into Supabase Vector Store.")
    print("Phase 1 Complete: Data & Knowledge Base are ready.")

if __name__ == "__main__":
    ingest_data()
