import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import vecs
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.database import Claim, engine

# --- CONFIG ---
TIMELY_FILING_DAYS = 90
HIGH_VALUE_THRESHOLD = 1000
SEMANTIC_RELEVANCE_THRESHOLD = 0.45  # max distance to consider a semantic match useful

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"]

# CPT code ranges for Place-of-Service check (Rule 3)
INPATIENT_CPT_RANGE = range(99221, 99234)   # 99221–99233
EMERGENCY_CPT_RANGE = range(99281, 99286)   # 99281–99285

# Gender-specific keywords (Rule 1)
FEMALE_ONLY_KEYWORDS = ["uterus", "ovary", "pap smear", "cesarean"]
MALE_ONLY_KEYWORDS = ["prostate", "testis"]

# Age-specific keywords (Rule 2)
ADULT_ONLY_KEYWORDS = ["geriatric", "medicare wellness", "colonoscopy"]
PEDIATRIC_ONLY_KEYWORDS = ["pediatric", "well-baby", "vaccine (pediatric)"]


class ClinicalAgent:
    def __init__(self):
        # 1. Setup Embedding Model
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")

        # 2. Setup Vector DB Connection (Supabase via vecs)
        db_url = os.getenv("DATABASE_URL", "")
        try:
            self.vx = vecs.create_client(db_url)
            self.collection = self.vx.get_or_create_collection(
                name="payer_policies",
                dimension=384,  # all-MiniLM-L6-v2 output dimension
            )
        except Exception:
            print("Warning: Vector DB not available. Run ingest.py!")
            self.vx = None
            self.collection = None

        # 3. Setup LLM (Azure OpenAI GPT-5 Reasoning Model)
        self.llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_DEPLOYMENT_NAME"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            model_kwargs={"reasoning_effort": "medium"},
        )

    # ------------------------------------------------------------------
    # UTILITY: Date Parser
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        if not date_str or not date_str.strip():
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------
    # STEP 1: Eligibility Check
    # ------------------------------------------------------------------
    def _check_eligibility(self, claim: Claim) -> dict | None:
        """Return a denial dict if the member_id is missing or invalid, else None."""
        if not claim.member_id or not claim.member_id.strip():
            return {
                "verdict": "DENIED",
                "confidence_score": 100,
                "reasoning": "Member ID is missing from the claim.",
                "missing_criteria": ["Valid Member ID"],
                "suggested_fix": "Ensure the claim includes a valid member ID before submission.",
                "step_failed": "Eligibility Check",
                "coding_flags": [],
            }

        # Medicare-specific validation
        if claim.payer_name and claim.payer_name.strip().lower() == "medicare":
            medicare_pattern = r"^[A-Za-z]?\d"
            if not re.match(medicare_pattern, claim.member_id.strip()):
                return {
                    "verdict": "DENIED",
                    "confidence_score": 100,
                    "reasoning": (
                        f"Medicare Member ID '{claim.member_id}' does not match "
                        "the expected format (must start with a digit or a valid "
                        "alpha prefix followed by digits)."
                    ),
                    "missing_criteria": ["Valid Medicare Member ID format"],
                    "suggested_fix": "Correct the Member ID to match the Medicare Beneficiary Identifier (MBI) format.",
                    "step_failed": "Eligibility Check",
                    "coding_flags": [],
                }

        return None  # passed

    # ------------------------------------------------------------------
    # STEP 2: Timely Filing Check
    # ------------------------------------------------------------------
    def _check_timely_filing(self, claim: Claim) -> dict | None:
        """Return a denial dict if submission is >90 days after service, else None."""
        dos = self._parse_date(claim.date_of_service)
        dsub = self._parse_date(claim.date_of_submission)

        if dos is None or dsub is None:
            return None  # cannot evaluate — let downstream steps decide

        delta = (dsub - dos).days
        if delta > TIMELY_FILING_DAYS:
            return {
                "verdict": "DENIED",
                "confidence_score": 100,
                "reasoning": (
                    f"Claim was submitted {delta} days after the date of service, "
                    f"exceeding the {TIMELY_FILING_DAYS}-day timely filing limit."
                ),
                "missing_criteria": ["Timely filing within 90 days of service"],
                "suggested_fix": "Re-submit with a valid appeal or proof of timely filing exception.",
                "step_failed": "Timely Filing Check",
                "coding_flags": [],
            }

        return None  # passed

    # ------------------------------------------------------------------
    # STEP 3 (NEW): Revenue Integrity / Coding Checks
    # ------------------------------------------------------------------
    def run_coding_checks(self, claim: Claim) -> list[str]:
        """
        Run 6 Revenue Integrity Rules against the claim.
        Returns a list of flag strings (DENIED / WARNING messages).

        Rules 1-3, 5 are deterministic.
        Rules 4, 6 are LLM-powered and batched into a single call.
        """
        flags: list[str] = []

        cpt_desc = (claim.cpt_description or "").lower()

        # ---- Rule 1: Gender Consistency ----
        gender = (claim.patient_gender or "").strip().upper()
        if gender == "M":
            for kw in FEMALE_ONLY_KEYWORDS:
                if kw in cpt_desc:
                    flags.append(
                        "DENIED: Gender Mismatch "
                        f"(Male patient billed for GYN procedure — CPT mentions '{kw}')"
                    )
                    break
        elif gender == "F":
            for kw in MALE_ONLY_KEYWORDS:
                if kw in cpt_desc:
                    flags.append(
                        "DENIED: Gender Mismatch "
                        f"(Female patient billed for Male-only procedure — CPT mentions '{kw}')"
                    )
                    break

        # ---- Rule 2: Age Appropriateness ("Benjamin Button" Rule) ----
        dob = self._parse_date(claim.patient_dob)
        dos = self._parse_date(claim.date_of_service)
        if dob and dos:
            age = (dos - dob).days // 365
            if age < 18:
                for kw in ADULT_ONLY_KEYWORDS:
                    if kw in cpt_desc:
                        flags.append(
                            f"WARNING: Age Mismatch "
                            f"(Pediatric patient aged {age} billed for Adult service — CPT mentions '{kw}')"
                        )
                        break
            elif age > 65:
                for kw in PEDIATRIC_ONLY_KEYWORDS:
                    if kw in cpt_desc:
                        flags.append(
                            f"WARNING: Age Mismatch "
                            f"(Senior patient aged {age} billed for Pediatric service — CPT mentions '{kw}')"
                        )
                        break

        # ---- Rule 3: Place of Service (POS) Mismatch ----
        pos = (claim.place_of_service or "").lower()
        if "office" in pos or "clinic" in pos:
            try:
                match = re.match(r"(\d+)", claim.cpt_code.strip())
                if match:
                    cpt_num = int(match.group(1))
                    if cpt_num in INPATIENT_CPT_RANGE or cpt_num in EMERGENCY_CPT_RANGE:
                        flags.append(
                            "DENIED: Site of Service Mismatch "
                            "(Hospital/ED code billed in Office setting)"
                        )
            except (ValueError, AttributeError):
                pass

        # ---- Rule 5: Prior Auth Guard ----
        prior_auth = (claim.prior_auth_number or "").strip().lower()
        has_prior_auth = prior_auth and prior_auth not in ("", "nan", "none", "n/a")
        if claim.claim_amount and claim.claim_amount > HIGH_VALUE_THRESHOLD and not has_prior_auth:
            flags.append(
                f"WARNING: Missing Prior Authorization for High-Value Claim "
                f"(${claim.claim_amount:,.0f})"
            )

        # ---- Rules 4 & 6: LLM-powered checks (batched into one call) ----
        llm_flags = self._run_llm_coding_checks(claim)
        flags.extend(llm_flags)

        return flags

    # ------------------------------------------------------------------
    # LLM-powered Coding Checks (Rules 4 + 6)
    # ------------------------------------------------------------------
    def _run_llm_coding_checks(self, claim: Claim) -> list[str]:
        """
        Rule 4 — Diagnosis vs. Procedure Logic ("Sanity Check")
        Rule 6 — Modifier Scout (bilateral / extra time)

        Batched into a single LLM call for efficiency.
        Returns a list of flag strings.
        """
        has_rule4_data = claim.icd_description and claim.cpt_description
        has_rule6_data = claim.transcription

        if not has_rule4_data and not has_rule6_data:
            return []

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a medical coding compliance auditor.
Evaluate the claim data below and return a JSON array of flag strings.
Only include flags that genuinely apply. Return an empty array [] if no issues found.

RULE 4 — Diagnosis vs. Procedure Logic:
Determine whether the diagnosis medically justifies the procedure.
If the diagnosis and procedure are clearly unrelated (e.g., "Headache" paired with "Cast Application, Leg"), add this exact flag:
"WARNING: Medical Necessity Mismatch (Diagnosis does not support Procedure)"

RULE 6 — Modifier Scout:
Review the transcription for evidence of:
  a) A bilateral procedure (both sides of the body) → expected modifier -50
  b) Significant extra time or complexity → expected modifier -22
If the transcription supports one of these but the current modifier does NOT include it, add:
"WARNING: Potential Missing Modifier -50 (Revenue Loss)" or
"WARNING: Potential Missing Modifier -22 (Revenue Loss)"

OUTPUT FORMAT — return ONLY a strict JSON array, no markdown fences:
["flag string 1", "flag string 2"]
or
[]"""),
            ("user", """Diagnosis (ICD): {icd_description}
Procedure (CPT): {cpt_description}
Current Modifier: {cpt_modifier}

Transcription (excerpt):
{transcription}""")
        ])

        chain = prompt_template | self.llm

        try:
            response = chain.invoke({
                "icd_description": claim.icd_description or "N/A",
                "cpt_description": claim.cpt_description or "N/A",
                "cpt_modifier": claim.cpt_modifier or "None",
                # Truncate transcription to stay within token limits
                "transcription": (claim.transcription or "N/A")[:3000],
            })

            raw = response.content.strip()
            # Strip markdown code fences if the LLM adds them
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            if isinstance(result, list):
                return [str(f) for f in result]
        except Exception:
            pass

        return []

    # ------------------------------------------------------------------
    # POLICY RESOLUTION — 3-Tier Strategy
    # ------------------------------------------------------------------
    def _resolve_policy(self, claim: Claim) -> tuple[str | None, str]:
        """
        Attempt to find a matching payer policy. Returns (policy_text, source).

        Tier 1 — Exact ID lookup in vecs collection.
        Tier 2 — Semantic search using the claim's clinical context.
        Tier 3 — Returns None (caller falls back to policy-free audit).
        """
        if not self.collection:
            return None, "none"

        # Tier 1: Exact ID match
        if claim.policy_id:
            try:
                records = self.collection.fetch(ids=[claim.policy_id])
                if records:
                    # fetch returns [(id, vector, metadata), ...]
                    metadata = records[0][2] if len(records[0]) > 2 else {}
                    policy_text = metadata.get("text")
                    if policy_text:
                        return policy_text, "exact_match"
            except Exception:
                pass  # ID not found — continue to Tier 2

        # Tier 2: Semantic search
        query_parts = [p for p in [
            claim.cpt_description,
            claim.icd_description,
            claim.medical_specialty,
            claim.denial_reason,
        ] if p]
        if query_parts:
            query_text = " | ".join(query_parts)
            query_vector = self.embed_model.encode(query_text).tolist()
            results = self.collection.query(
                data=query_vector,
                limit=1,
                include_value=True,
                include_metadata=True,
            )
            if results:
                # query returns [(id, distance, metadata), ...]
                matched_id, distance, metadata = results[0]
                if distance <= SEMANTIC_RELEVANCE_THRESHOLD:
                    policy_text = metadata.get("text", "")
                    return policy_text, f"semantic_match ({matched_id}, dist={distance:.2f})"

        # Tier 3: No policy found
        return None, "none"

    # ------------------------------------------------------------------
    # MAIN PIPELINE — verify_claim
    # ------------------------------------------------------------------
    def verify_claim(self, claim_id: int):
        """
        Multi-Step Verification Pipeline:
          Step 1 — Eligibility Check
          Step 2 — Timely Filing Check
          Step 3 — Revenue Integrity / Coding Checks
          Step 4 — RAG Clinical Policy Check (3-tier resolution)
          Step 5 — Merge output with coding_flags & confidence_score
        """
        # --- Load Claim ---
        with Session(engine) as session:
            claim = session.get(Claim, claim_id)
            if not claim:
                return {"status": "error", "message": "Claim not found"}

            # Step 1: Eligibility
            eligibility_result = self._check_eligibility(claim)
            if eligibility_result is not None:
                return eligibility_result

            # Step 2: Timely Filing
            filing_result = self._check_timely_filing(claim)
            if filing_result is not None:
                return filing_result

            # Step 3: Revenue Integrity / Coding Checks
            coding_flags = self.run_coding_checks(claim)

            # Step 4: Resolve policy (3-tier) + LLM analysis
            policy_text, policy_source = self._resolve_policy(claim)

            try:
                if policy_text:
                    llm_raw = self._analyze_with_llm(claim, policy_text)
                else:
                    llm_raw = self._analyze_without_policy(claim)
            except Exception as e:
                return {
                    "verdict": "WARNING",
                    "confidence_score": 0,
                    "reasoning": f"LLM analysis failed: {e}",
                    "missing_criteria": [],
                    "suggested_fix": "Check Azure OpenAI deployment configuration (.env).",
                    "coding_flags": coding_flags,
                    "policy_source": policy_source,
                    "step_failed": "LLM Analysis",
                }

            # Step 5: Merge
            result = self._parse_llm_response(llm_raw)
            result["coding_flags"] = coding_flags
            result["policy_source"] = policy_source

            return result

    # ------------------------------------------------------------------
    # LLM ANALYSIS (RAG Clinical Check)
    # ------------------------------------------------------------------
    def _analyze_with_llm(self, claim: Claim, policy_text: str) -> str:
        """
        Uses Chain-of-Thought prompting to compare notes vs policy.
        Returns the raw LLM response string.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Medical Auditor for insurance claims.
            Your goal is to prevent denials by strictly comparing Doctor Notes against Payer Policies.

            Input:
            1. Doctor's Transcription
            2. Payer Policy Text
            3. Full Claim Details (CPT, ICD, modifiers, dates, prior auth, etc.)

            Task:
            1. Extract the specific medical criteria required by the Policy.
            2. Check if the Doctor's Transcription explicitly mentions these criteria.
            3. Verify the CPT code and modifier are consistent with the documentation.
            4. Check if ICD diagnosis codes align with the procedure and policy requirements.
            5. Flag any prior authorization issues if applicable.
            6. Return a verdict: 'APPROVED', 'DENIED', or 'WARNING'.
            7. If WARNING or DENIED, cite the specific missing phrase or criteria.
            """),
            ("user", """
            --- PAYER POLICY ({policy_id}) ---
            {policy_text}

            --- DOCTOR'S TRANSCRIPTION ---
            {transcription}

            --- CLAIM DETAILS ---
            CPT Code: {cpt_code}
            CPT Description: {cpt_description}
            CPT Modifier: {cpt_modifier}
            ICD Code: {icd_code}
            ICD Description: {icd_description}
            Medical Specialty: {medical_specialty}
            Denial Code: {denial_code}
            Denial Reason: {denial_reason}
            Payer: {payer_name}
            Plan Type: {plan_type}
            Prior Auth Number: {prior_auth_number}
            Claim Amount: ${claim_amount}
            Date of Service: {date_of_service}
            Place of Service: {place_of_service}
            Facility: {facility_name}

            OUTPUT FORMAT (JSON):
            {{
                "verdict": "APPROVED" | "DENIED" | "WARNING",
                "confidence_score": 0-100,
                "reasoning": "Brief explanation citing the policy.",
                "missing_criteria": ["List of missing elements if any"],
                "suggested_fix": "What the doctor should add to the note."
            }}
            """)
        ])

        chain = prompt_template | self.llm

        response = chain.invoke({
            "policy_id": claim.policy_id or "N/A",
            "policy_text": policy_text,
            "transcription": claim.transcription or "N/A",
            "cpt_code": claim.cpt_code or "N/A",
            "cpt_description": claim.cpt_description or "N/A",
            "cpt_modifier": claim.cpt_modifier or "None",
            "icd_code": claim.icd_code or "N/A",
            "icd_description": claim.icd_description or "N/A",
            "medical_specialty": claim.medical_specialty or "N/A",
            "denial_code": claim.denial_code or "None",
            "denial_reason": claim.denial_reason or "None",
            "payer_name": claim.payer_name or "N/A",
            "plan_type": claim.plan_type or "N/A",
            "prior_auth_number": claim.prior_auth_number or "None",
            "claim_amount": claim.claim_amount if claim.claim_amount else "N/A",
            "date_of_service": claim.date_of_service or "N/A",
            "place_of_service": claim.place_of_service or "N/A",
            "facility_name": claim.facility_name or "N/A",
        })

        return response.content

    # ------------------------------------------------------------------
    # LLM ANALYSIS — Policy-Free (Tier 3 Fallback)
    # ------------------------------------------------------------------
    def _analyze_without_policy(self, claim: Claim) -> str:
        """
        When no matching policy exists in the knowledge base, perform a
        general medical-necessity audit using the LLM's own clinical knowledge.
        """
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Medical Auditor for insurance claims.
            No specific payer policy document is available for this claim.
            Use your general knowledge of medical billing standards, CMS/Medicare
            guidelines, and standard-of-care practices to audit the claim.

            Task:
            1. Assess whether the Doctor's Transcription supports the billed procedure.
            2. Verify CPT code, modifier, and ICD diagnosis alignment.
            3. Flag any documentation gaps or coding inconsistencies.
            4. Return a verdict: 'APPROVED', 'DENIED', or 'WARNING'.
            5. Be transparent that no specific policy was matched.
            """),
            ("user", """
            --- NOTE: No specific payer policy was found for this claim. ---
            --- Performing general medical necessity review. ---

            --- DOCTOR'S TRANSCRIPTION ---
            {transcription}

            --- CLAIM DETAILS ---
            CPT Code: {cpt_code}
            CPT Description: {cpt_description}
            CPT Modifier: {cpt_modifier}
            ICD Code: {icd_code}
            ICD Description: {icd_description}
            Medical Specialty: {medical_specialty}
            Denial Code: {denial_code}
            Denial Reason: {denial_reason}
            Payer: {payer_name}
            Plan Type: {plan_type}
            Prior Auth Number: {prior_auth_number}
            Claim Amount: ${claim_amount}
            Date of Service: {date_of_service}
            Place of Service: {place_of_service}
            Facility: {facility_name}

            OUTPUT FORMAT (JSON):
            {{
                "verdict": "APPROVED" | "DENIED" | "WARNING",
                "confidence_score": 0-100,
                "reasoning": "Brief explanation. Note that no specific policy was available.",
                "missing_criteria": ["List of missing elements if any"],
                "suggested_fix": "What the doctor should add to the note."
            }}
            """)
        ])

        chain = prompt_template | self.llm

        response = chain.invoke({
            "transcription": claim.transcription or "N/A",
            "cpt_code": claim.cpt_code or "N/A",
            "cpt_description": claim.cpt_description or "N/A",
            "cpt_modifier": claim.cpt_modifier or "None",
            "icd_code": claim.icd_code or "N/A",
            "icd_description": claim.icd_description or "N/A",
            "medical_specialty": claim.medical_specialty or "N/A",
            "denial_code": claim.denial_code or "None",
            "denial_reason": claim.denial_reason or "None",
            "payer_name": claim.payer_name or "N/A",
            "plan_type": claim.plan_type or "N/A",
            "prior_auth_number": claim.prior_auth_number or "None",
            "claim_amount": claim.claim_amount if claim.claim_amount else "N/A",
            "date_of_service": claim.date_of_service or "N/A",
            "place_of_service": claim.place_of_service or "N/A",
            "facility_name": claim.facility_name or "N/A",
        })

        return response.content

    # ------------------------------------------------------------------
    # UTILITY: Parse LLM JSON response
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_llm_response(raw: str) -> dict:
        """Parse the LLM string output into a dict, handling markdown fences."""
        if isinstance(raw, dict):
            return raw
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, AttributeError):
            return {"raw_output": raw}


# Singleton instance
clinical_agent = ClinicalAgent()
