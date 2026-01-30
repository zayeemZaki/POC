"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API = "http://localhost:8000";

interface Claim {
  id: number;
  patient_id: string;
  description: string;
  medical_specialty: string | null;
  transcription: string | null;
  cpt_code: string;
  cpt_description: string | null;
  cpt_modifier: string | null;
  icd_code: string | null;
  icd_description: string | null;
  payer_name: string | null;
  plan_type: string | null;
  policy_id: string | null;
  member_id: string | null;
  claim_number: string | null;
  claim_amount: number | null;
  date_of_service: string | null;
  date_of_submission: string | null;
  denial_code: string | null;
  denial_reason: string | null;
  prior_auth_number: string | null;
  facility_name: string | null;
  place_of_service: string | null;
  provider_npi: string | null;
  status: string;
}

interface AuditResult {
  verdict: "APPROVED" | "DENIED" | "WARNING";
  confidence_score: number;
  reasoning: string;
  missing_criteria: string[];
  suggested_fix: string;
  step_failed?: string;
  coding_flags?: string[];
  policy_source?: string;
  status?: string;
  message?: string;
  raw_output?: string;
}

function getStatusText(status: string) {
  const normalized = status.toUpperCase();
  if (normalized === "DENIED") {
    return <span className="font-bold text-black">{normalized}</span>;
  }
  return <span className="text-gray-500">{normalized}</span>;
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="py-2 border-b border-gray-200">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-black mt-1">{value || "—"}</p>
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-3 pb-2 border-b border-black">
      <h3 className="text-xs font-bold text-black uppercase tracking-wider">{title}</h3>
    </div>
  );
}

export default function ClaimDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [auditing, setAuditing] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchClaim() {
      try {
        const res = await fetch(`${API}/claims/${id}`);
        if (!res.ok) throw new Error(`Claim not found (${res.status})`);
        const data = await res.json();
        setClaim(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load claim");
      } finally {
        setLoading(false);
      }
    }
    fetchClaim();
  }, [id]);

  async function runAudit() {
    setAuditing(true);
    setAuditError(null);
    setAudit(null);
    
    try {
      const res = await fetch(`${API}/verify/${id}`, { method: "POST" });
      if (!res.ok) throw new Error(`Verification failed (${res.status})`);
      const data: AuditResult = await res.json();
      setAudit(data);
    } catch (err: unknown) {
      setAuditError(err instanceof Error ? err.message : "Audit failed");
    } finally {
      setAuditing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <p className="text-sm text-black">LOADING...</p>
      </div>
    );
  }
  
  if (error || !claim) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-white">
        <p className="text-sm font-bold text-black">ERROR</p>
        <p className="text-sm text-gray-500">{error || "Claim not found"}</p>
        <Link href="/" className="text-xs text-black underline">
          RETURN TO WORKLIST
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="border-b border-black bg-white flex-shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xs text-black underline">
              RETURN
            </Link>
            <div className="flex-1">
              <h1 className="text-sm font-bold text-black uppercase tracking-wide">
                Claim {claim.id} — Patient {claim.patient_id}
              </h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-gray-500 uppercase">
                  {claim.medical_specialty || "General"} • {claim.payer_name || "Unknown Payer"}
                </span>
                <span className="text-xs">
                  {getStatusText(claim.status)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 3-Column Grid - No Gaps, Harsh Borders */}
      <main className="flex-1 overflow-hidden flex">
        {/* COLUMN 1: Clinical Documentation */}
        <section className="w-1/3 flex flex-col border-r border-black overflow-hidden bg-white">
          <div className="border-b border-black px-4 py-3 flex-shrink-0">
            <h2 className="text-xs font-bold text-black uppercase tracking-wide">Clinical Documentation</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto px-4 py-4">
            <div className="mb-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Chief Complaint</p>
              <p className="text-sm text-black leading-relaxed">{claim.description}</p>
            </div>
            
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Medical Record</p>
              <div className="border border-gray-300 p-3 text-xs font-mono text-black leading-relaxed whitespace-pre-wrap bg-white">
                {claim.transcription || "No clinical documentation available."}
              </div>
            </div>
          </div>
        </section>

        {/* COLUMN 2: Coding & Billing */}
        <section className="w-1/3 flex flex-col border-r border-black overflow-hidden bg-white">
          <div className="border-b border-black px-4 py-3 flex-shrink-0">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-black uppercase tracking-wide">Coding & Billing</h2>
              {claim.claim_amount != null && claim.claim_amount > 1000 && (
                <span className="text-xs font-bold text-black">[HIGH VALUE]</span>
              )}
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
            <div>
              <SectionHeader title="Patient Demographics" />
              <Field label="Patient ID" value={claim.patient_id} />
              <Field label="Member ID" value={claim.member_id} />
              <Field label="Specialty" value={claim.medical_specialty} />
            </div>

            <div>
              <SectionHeader title="Procedure & Diagnosis" />
              <Field label="CPT Code" value={`${claim.cpt_code}${claim.cpt_modifier ? ` - ${claim.cpt_modifier}` : ""}`} />
              <Field label="CPT Description" value={claim.cpt_description} />
              <Field label="ICD-10 Code" value={claim.icd_code} />
              <Field label="Diagnosis" value={claim.icd_description} />
              <Field label="Date of Service" value={claim.date_of_service} />
            </div>

            <div>
              <SectionHeader title="Financial Information" />
              <Field label="Claim Amount" value={claim.claim_amount != null ? `$${claim.claim_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : null} />
              <Field label="Payer" value={claim.payer_name} />
              <Field label="Plan Type" value={claim.plan_type} />
              <Field label="Policy ID" value={claim.policy_id} />
              <Field label="Claim Number" value={claim.claim_number} />
            </div>

            <div>
              <SectionHeader title="Additional Information" />
              <Field label="Facility" value={claim.facility_name} />
              <Field label="Prior Auth Number" value={claim.prior_auth_number} />
              <Field label="Submission Date" value={claim.date_of_submission} />
              {claim.denial_reason && (
                <div className="pt-2 mt-2 border-t border-gray-300">
                  <Field label="Denial Reason" value={`${claim.denial_code || ""} — ${claim.denial_reason}`} />
                </div>
              )}
            </div>
          </div>
        </section>

        {/* COLUMN 3: Verification Results */}
        <section className="w-1/3 flex flex-col overflow-hidden bg-white">
          <div className="border-b border-black px-4 py-3 flex-shrink-0">
            <h2 className="text-xs font-bold text-black uppercase tracking-wide">Verification Results</h2>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {!audit && !auditing && !auditError && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-6">Ready to Audit</p>
                <button
                  onClick={runAudit}
                  className="border border-black bg-white px-6 py-2 text-xs font-bold text-black uppercase tracking-wide hover:bg-gray-100 transition-colors"
                >
                  Run Verification
                </button>
              </div>
            )}

            {auditing && (
              <div className="text-center py-6">
                <p className="text-xs text-black font-bold uppercase tracking-wide mb-2">Processing...</p>
                <p className="text-xs text-gray-500">Running verification</p>
              </div>
            )}

            {auditError && (
              <div className="border border-black p-4">
                <p className="text-xs font-bold text-black uppercase mb-1">[ERROR]</p>
                <p className="text-xs text-gray-700">{auditError}</p>
              </div>
            )}

            {audit && !auditing && (
              <div className="space-y-4">
                {audit.status === "warning" || audit.status === "error" ? (
                  <>
                    <div className="border border-black p-4">
                      <p className="text-xs font-bold text-black uppercase mb-2">[{audit.status}]</p>
                      <p className="text-xs text-gray-700">{audit.message}</p>
                    </div>
                    
                    {audit.coding_flags && audit.coding_flags.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-black uppercase mb-2">Coding Alerts</p>
                        <ul className="space-y-2">
                          {audit.coding_flags.map((flag, i) => (
                            <li key={i} className="border border-gray-300 px-3 py-2 text-xs text-black">
                              {flag}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : audit.raw_output ? (
                  <div className="border border-gray-300 p-4">
                    <p className="text-xs text-gray-500 uppercase mb-2">Raw Output</p>
                    <p className="text-xs text-black whitespace-pre-wrap font-mono">{audit.raw_output}</p>
                  </div>
                ) : (
                  <>
                    <div className="border border-black p-4">
                      <p className="text-xs font-bold text-black uppercase mb-2">[{audit.verdict}]</p>
                      {audit.step_failed && (
                        <p className="text-xs text-gray-500 uppercase mb-1">Failed: {audit.step_failed}</p>
                      )}
                      <p className="text-xs text-black leading-relaxed mb-2">{audit.reasoning}</p>
                      {audit.policy_source && (
                        <p className="text-xs text-gray-500 mt-2">Source: {audit.policy_source}</p>
                      )}
                    </div>

                    {audit.confidence_score != null && (
                      <div className="border border-gray-300 p-4">
                        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Confidence</p>
                        <p className="text-sm font-bold text-black">{audit.confidence_score}%</p>
                      </div>
                    )}

                    {audit.coding_flags && audit.coding_flags.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-black uppercase mb-2">Coding Alerts</p>
                        <ul className="space-y-2">
                          {audit.coding_flags.map((flag, i) => {
                            const isDenied = flag.startsWith("DENIED");
                            return (
                              <li key={i} className="border border-gray-300 px-3 py-2 text-xs text-black">
                                {isDenied && <span className="font-bold">[DENIED] </span>}
                                {flag}
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}

                    {audit.missing_criteria && audit.missing_criteria.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-black uppercase mb-2">Missing Criteria</p>
                        <ul className="space-y-2">
                          {audit.missing_criteria.map((item, i) => (
                            <li key={i} className="border border-gray-300 px-3 py-2 text-xs text-black">
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {audit.suggested_fix && (
                      <div className="border border-black p-4">
                        <p className="text-xs font-bold text-black uppercase mb-2">Suggested Action</p>
                        <p className="text-xs text-black leading-relaxed">{audit.suggested_fix}</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
