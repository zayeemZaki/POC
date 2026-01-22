import sys
import os
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from sqlmodel import Session, select

# Add parent dir to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Claim, create_db_and_tables, engine

CSV_PATH = "data/poc_dataset.csv"
CHROMA_PATH = "chroma_db"

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
    print(f"Starting Ingestion Phase...")
    
    # Initialize DB
    create_db_and_tables()
    
    # Load CSV
    if not os.path.exists(CSV_PATH):
        print(f"Error: File not found at {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    # Normalize column names to match our Model (lower case, underscores)
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    
    # Insert into SQLite
    with Session(engine) as session:
        # Check if empty
        existing = session.exec(select(Claim)).first()
        if existing:
            print("Database already has data. Skipping SQL ingestion.")
        else:
            print(f"Importing {len(df)} rows into SQLite...")
            for _, row in df.iterrows():
                claim = Claim(
                    patient_id=str(row.get("patient_id")),
                    description=str(row.get("description")),
                    transcription=str(row.get("transcription")),
                    cpt_code=str(row.get("cpt_code")),
                    denial_code=str(row.get("denial_code")),
                    payer_name=str(row.get("payer_name")),
                    policy_id=str(row.get("policy_id", "")),
                    claim_amount=float(row.get("claim_amount", 0.0)) if pd.notnull(row.get("claim_amount")) else 0.0
                )
                session.add(claim)
            session.commit()
            print("SQL Data Ingested Successfully.")

    # Ingest RAG (Vector DB)
    print("🧠 Ingesting Policies into Vector DB...")
    
    # Use a local embedding model
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Delete collection if exists to start fresh
    try:
        client.delete_collection(name="payer_policies")
    except:
        pass
        
    collection = client.create_collection(name="payer_policies", embedding_function=ef)
    
    # Prepare Data for Chroma
    ids = [p["policy_id"] for p in MOCK_POLICIES]
    documents = [p["text"] for p in MOCK_POLICIES]
    metadatas = [{"title": p["title"]} for p in MOCK_POLICIES]
    
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Indexed {len(documents)} policies into ChromaDB.")
    print("Phase 1 Complete: Data & Knowledge Base are ready.")

if __name__ == "__main__":
    ingest_data()