from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select

# "Claim" Model - should match the CSV structure closely
class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: str
    description: str  # This is the "Doctor Note"
    medical_specialty: Optional[str] = None
    transcription: str = Field(sa_column_kwargs={"nullable": True})
    cpt_code: str
    denial_code: Optional[str] = None
    denial_reason: Optional[str] = None
    payer_name: Optional[str] = None
    policy_id: Optional[str] = None 
    claim_amount: Optional[float] = None
    status: str = Field(default="Pending") 

# Database Setup
sqlite_file_name = "claims.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session