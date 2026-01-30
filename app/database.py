import os
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select

# "Claim" Model - matches the full CSV structure
class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: str
    description: str  # This is the "Doctor Note"
    medical_specialty: Optional[str] = None
    sample_name: Optional[str] = None
    transcription: Optional[str] = Field(default=None, sa_column_kwargs={"nullable": True})
    keywords: Optional[str] = None
    cpt_code: str
    cpt_description: Optional[str] = None
    cpt_modifier: Optional[str] = None
    icd_code: Optional[str] = None
    icd_description: Optional[str] = None
    bill_type: Optional[str] = None
    provider_specialty: Optional[str] = None
    denial_code: Optional[str] = None
    denial_reason: Optional[str] = None
    member_id: Optional[str] = None
    payer_name: Optional[str] = None
    plan_type: Optional[str] = None
    policy_id: Optional[str] = None
    claim_number: Optional[str] = None
    group_number: Optional[str] = None
    provider_npi: Optional[str] = None
    facility_name: Optional[str] = None
    place_of_service: Optional[str] = None
    date_of_service: Optional[str] = None
    date_of_submission: Optional[str] = None
    date_of_denial: Optional[str] = None
    prior_auth_number: Optional[str] = None
    claim_amount: Optional[float] = None
    patient_dob: Optional[str] = None
    patient_gender: Optional[str] = None
    status: str = Field(default="Pending")

# Database Setup
if os.getenv("RAILWAY_VOLUME_MOUNT_PATH"):
    sqlite_file_name = f"{os.getenv('RAILWAY_VOLUME_MOUNT_PATH')}/claims.db"
else:
    sqlite_file_name = "claims.db"
    
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
