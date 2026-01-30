"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API = "http://localhost:8000";

// --- Types ---

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
  // Fallback fields for non-LLM responses
  status?: string;
  message?: string;
  raw_output?: string;
}

// --- Helpers ---

function getStatusText(status: string) {
  const normalized = status.toUpperCase();
  if (normalized === "DENIED") {
    return <span className="font-bold text-black">{normalized}</span>;
  }
  return <span className="text-gray-500">{normalized}</span>;
}

// --- Field Row Component ---

function Field({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | null | undefined }) {
  return (
    <div className="flex items-start gap-2 py-2">
      <span className="mt-0.5 text-slate-400 flex-shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-600 tracking-wide">{label}</p>
        <p className="text-sm text-slate-900 font-medium mt-0.5">{value || "—"}</p>
      </div>
    </div>
  );
}

// --- Section Header Component ---

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-3 pb-2 border-b border-black">
      <h3 className="text-xs font-bold text-black uppercase tracking-wider">{title}</h3>
    </div>
  );
}

// --- Main Page ---

export default function ClaimDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [auditing, setAuditing] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  // --- Fetch claim on mount ---
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

  // --- Run Audit with Loading Animation ---
  async function ru---
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
      setAuditing(false
  }

  // --- Loading / Error states ---
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }
  if (error || !claim) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-slate-50">
        <ShieldX className="h-12 w-12 text-red-400" />
        <p className="text-lg text-red-600">{error || "Claim not found"}</p>
        <Link href="/" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
          ← Back to Worklist
        </Link>
      </div>white">
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
          RETURN TO WORKLISTlassName="text-slate-400 hover:text-slate-600 transition-colors">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-lg font-semibold text-slate-900">
                Claim #{claim.id} — Patient {claim.patient_id}
              </h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-sm text-slate-600">
                  {claim.medical_specialty || "General"} • {claim.payer_name || "Unknown Payer"}
                </span>
                <span
                  className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getStatusBadge(claim.status)}`}
                >
                  {claim.status}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 3-Column "Cockpit" Grid - Fixed Height with 30/35/35 Split */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full px-6 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-10 gap-5 h-full">
            {/* ======== COLUMN 1: Clinical Documentation (30% = 3/10) ======== */}
            <section className="lg:col-span-3 flex flex-col rounded-lg border border-slate-200 bg-white shadow-md overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 flex-shrink-0 bg-gradient-to-r from-amber-50 to-white">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-amber-600" />
                  <h2 className="font-semibold text-slate-900">Clinical Documentation</h2>
                </div>
                <div className="flex items-center gap-1">
                  <button className="p-1.5 hover:bg-slate-100 rounded transition-colors" title="Copy">
                    <Copy className="h-4 w-4 text-slate-400" />
                  </button>
                  <button className="p-1.5 hover:bg-slate-100 rounded transition-colors" title="Expand">
                    <Expand className="h-4 w-4 text-slate-400" />
                  </button>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto px-4 py-4 bg-amber-50/30">
                {/* Chief Complaint */}
                <div className="mb-4">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Chief Complaint</p>
                  <p className="text-sm text-slate-800 leading-relaxed">{claim.description}</p>
                </div>
                
                {/* Medical Record (Monospaced) */}
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">Medical Record</p>
                  <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-xs font-mono text-slate-800 leading-relaxed whitespace-pre-wrap shadow-inner">
                    {claim.transcription || "No clinical documentation available."}
                  </div>
                </div>
              </div>
            </section>

            {/* ======== COLUMN 2: Coding & Billing (35% = 3.5/10) ======== */}
            <section className="lg:col-span-4 flex flex-col rounded-lg border border-slate-200 bg-white shadow-md overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <ClipboardList className="h-5 w-5 text-blue-600" />
                  <h2 className="font-semibold text-slate-900">Coding & Billing</h2>
                </div>
                {claim.claim_amount != null && claim.claim_amount > 1000 && (
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
                    <TrendingUp className="h-3.5 w-3.5" />
                    High Value
                  </span>
                )}
              </div>
              
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
                {/* Patient Demographics */}
                <div>
                  <SectionHeader title="Patient Demographics" />
                  <div className="space-y-2">
                    <Field icon={<User className="h-4 w-4" />} label="Patient ID" value={claim.patient_id} />
                    <Field icon={<Hash className="h-4 w-4" />} label="Member ID" value={claim.member_id} />
                    <Field icon={<Stethoscope className="h-4 w-4" />} label="Specialty" value={claim.medical_specialty} />
                  </div>
                </div>

                {/* Procedure Details */}
                <div>
                  <SectionHeader title="Procedure & Diagnosis" />
                  <div className="space-y-2">
                    <Field 
                      icon={<Hash className="h-4 w-4" />} 
                      label="CPT Code" 
                      value={`${claim.cpt_code}${claim.cpt_modifier ? ` - ${claim.cpt_modifier}` : ""}`} 
                    />
                    <Field icon={<FileText className="h-4 w-4" />} label="CPT Description" value={claim.cpt_description} />
                    <Field icon={<Hash className="h-4 w-4" />} label="ICD-10 Code" value={claim.icd_code} />
                    <Field icon={<FileText className="h-4 w-4" />} label="Diagnosis" value={claim.icd_description} />
                    <Field icon={<Calendar className="h-4 w-4" />} label="Date of Service" value={claim.date_of_service} />
                  </div>
                </div>

                {/* Financials */}
                <div>
                  <SectionHeader title="Financial Information" />
                  <div className="space-y-2">
                    <Field 
                      icon={<DollarSign className="h-4 w-4" />} 
                      label="Claim Amount" 
                      value={claim.claim_amount != null ? `$${claim.claim_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : null} 
                    />
                    <Field icon={<Building2 className="h-4 w-4" />} label="Payer" value={claim.payer_name} />
                    <Field icon={<FileText className="h-4 w-4" />} label="Plan Type" value={claim.plan_type} />
                    <Field icon={<Hash className="h-4 w-4" />} label="Policy ID" value={claim.policy_id} />
                    <Field icon={<Hash className="h-4 w-4" />} label="Claim Number" value={claim.claim_number} />
                  </div>
                </div>

                {/* Additional Info */}
                <div>
                  <SectionHeader title="Additional Information" />
                  <div className="space-y-2">
                    <Field icon={<Building2 className="h-4 w-4" />} label="Facility" value={claim.facility_name} />
                    <Field icon={<Hash className="h-4 w-4" />} label="Prior Auth Number" value={claim.prior_auth_number} />
                    <Field icon={<Calendar className="h-4 w-4" />} label="Submission Date" value={claim.date_of_submission} />
                    {claim.denial_reason && (
                      <div className="pt-2 mt-2 border-t border-red-100">
                        <Field 
                          icon={<XCircle className="h-4 w-4 text-red-500" />} 
                          label="Denial Reason" 
                          value={`${claim.denial_code || ""} — ${claim.denial_reason}`} 
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* ======== COLUMN 3: Live Verification Agent (35% = 3.5/10) ======== */}
            <section className="lg:col-span-3 flex flex-col rounded-lg border border-slate-200 bg-white shadow-md overflow-hidden">
              <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3 flex-shrink-0 bg-gradient-to-r from-purple-50 to-white">
                <Sparkles className="h-5 w-5 text-purple-600" />
                <h2 className="font-semibold text-slate-900">Live Verification Agent</h2>
              </div>

              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                {/* STATE 1: Idle / Ready State */}
                {!audit && !auditing && !auditError && (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 p-6 mb-4">
                      <Bot className="h-12 w-12 text-indigo-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">Ready to Scan</h3>
                    <p className="text-sm text-slate-600 mb-6 max-w-xs">
                      AI-powered verification engine ready to validate claim against payer policies
                    </p>
                    <button
                      onClick={runAudit}
                      className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-lg transition-all hover:shadow-xl hover:scale-105"
                    >
                      <Play className="h-4 w-4" />
                      Run Audit
                    </button>
                  </div>
                )}

                {/* STATE 2: Loading / Processing State */}
                {auditing && (
                  <div className="space-y-4">
                    <div className="text-center py-6">
                      <div className="inline-flex items-center justify-center rounded-full bg-indigo-100 p-4 mb-4">
                        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                      </div>
                      <h3 className="text-lg font-semibold text-slate-900 mb-1">Processing Claim</h3>
                      <p className="text-sm text-slate-600">Running multi-step verification</p>
                    </div>
                    
                    <div className="space-y-2">
                      <LoadingStep step="Checking Eligibility..." active={loadingStep === 0} />
                      <LoadingStep step="Reading Policy Documents..." active={loadingStep === 1} />
                      <LoadingStep step="Validating Medical Codes..." active={loadingStep === 2} />
                    </div>
                  </div>
                )}

                {/* Audit Error */}
                {auditError && (
                  <div className="rounded-lg border-2 border-red-300 bg-red-50 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <XCircle className="h-5 w-5 text-red-600" />
                      <span className="font-semibold text-red-800">Error</span>
                    </div>
                    <p className="text-sm text-red-700">{auditError}</p>
                  </div>
                )}

                {/* STATE 3: Results State */}
                {audit && !auditing && (
                  <div className="space-y-4">
                    {/* Handle Warnings/Errors from Pipeline */}
                    {audit.status === "warning" || audit.status === "error" ? (
                      <>
                        <div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-4">
                          <div className="flex items-center gap-3 mb-2">
                            <AlertTriangle className="h-6 w-6 text-amber-600" />
                            <span className="text-lg font-bold text-amber-800 capitalize">{audit.status}</span>
                          </div>
                          <p className="text-sm text-amber-700">{audit.message}</p>
                        </div>
                        
                        {/* Coding Flags Section */}
                        {audit.coding_flags && audit.coding_flags.length > 0 && (
                          <div>
                            <SectionHeader title="⚠️ Coding Alerts" />
                            <ul className="space-y-2">
                              {audit.coding_flags.map((flag, i) => {
                                const isDenied = flag.startsWith("DENIED");
                                return (
                                  <li
                                    key={i}
                                    className={`flex items-start gap-2 rounded-lg border-2 px-3 py-2.5 text-sm ${
                                      isDenied
                                        ? "bg-red-50 border-red-200 text-red-900"
                                        : "bg-amber-50 border-amber-200 text-amber-900"
                                    }`}
                                  >
                                    <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${isDenied ? "text-red-500" : "text-amber-500"}`} />
                                    <span className="font-medium">{flag}</span>
                                  </li>
                                );
                              })}
                            </ul>
                          </div>
                        )}
                      </>
                    ) : audit.raw_output ? (
                      <div className="rounded-lg border border-slate-300 bg-slate-50 p-4">
                        <p className="text-xs font-semibold text-slate-600 uppercase mb-2">Raw Output</p>
                        <p className="text-sm text-slate-700 whitespace-pre-wrap font-mono">{audit.raw_output}</p>
                      </div>
                    ) : (
                      <>
                        {/* VERDICT BANNER - Large Color-Coded Card */}
                        <div className={`rounded-xl border-2 p-5 shadow-lg ${verdictColor(audit.verdict)}`}>
                          <div className="flex items-center gap-3 mb-3">
                            {verdictIcon(audit.verdict)}
                            <div>
                              <span className="text-2xl font-bold block">{audit.verdict}</span>
                              {audit.step_failed && (
                                <span className="text-xs opacity-75">Failed: {audit.step_failed}</span>
                              )}
                            </div>
                          </div>
                          <p className="text-sm leading-relaxed mb-2">{audit.reasoning}</p>
                          {audit.policy_source && (
                            <p className="text-xs opacity-70 mt-2">
                              Source: <span className="font-mono">{audit.policy_source}</span>
                            </p>
                          )}
                        </div>

                        {/* CONFIDENCE SCORE - Visual Progress Bar */}
                        {audit.confidence_score != null && (
                          <div className="bg-slate-50 rounded-lg border border-slate-200 p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                                Confidence Score
                              </span>
                              <span className="text-xl font-bold text-slate-900">
                                {audit.confidence_score}%
                              </span>
                            </div>
                            <div className="h-4 w-full rounded-full bg-slate-200 overflow-hidden shadow-inner">
                              <div
                                className={`h-full rounded-full transition-all duration-1000 ${confidenceBarColor(audit.confidence_score)}`}
                                style={{ width: `${audit.confidence_score}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* CODING FLAGS SECTION - Distinct Warning Alerts */}
                        {audit.coding_flags && audit.coding_flags.length > 0 && (
                          <div>
                            <SectionHeader title="⚠️ Coding Alerts" />
                            <ul className="space-y-2">
                              {audit.coding_flags.map((flag, i) => {
                                const isDenied = flag.startsWith("DENIED");
                                return (
                                  <li
                                    key={i}
                                    className={`flex items-start gap-2 rounded-lg border-2 px-3 py-2.5 text-sm ${
                                      isDenied
                                        ? "bg-red-50 border-red-200 text-red-900"
                                        : "bg-amber-50 border-amber-200 text-amber-900"
                                    }`}
                                  >
                                    <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${isDenied ? "text-red-500" : "text-amber-500"}`} />
                                    <span className="font-medium">{flag}</span>
                                  </li>
                                );
                              })}
                            </ul>
                          </div>
                        )}

                        {/* MEDICAL NECESSITY SECTION */}
                        {audit.missing_criteria && audit.missing_criteria.length > 0 && (
                          <div>
                            <SectionHeader title="Missing Criteria" />
                            <ul className="space-y-2">
                              {audit.missing_criteria.map((item, i) => (
                                <li
                                  key={i}
                                  className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-900"
                                >
                                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* SUGGESTED FIX */}
                        {audit.suggested_fix && (
                          <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <CheckCircle2 className="h-5 w-5 text-blue-600" />
                              <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">
                                Suggested Action
                              </span>
                            </div>
                            <p className="text-sm text-blue-900 leading-relaxed">{audit.suggested_fix}</p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

                {/* Empty state */}
                {!audit && !auditing && !auditError && (
                  <div className="flex flex-col items-center justify-center py-12 text-center text-slate-400">
                    <Bot className="h-10 w-10 mb-3 opacity-40" />
                    <p className="text-sm">Click &quot;Run Audit&quot; to verify this claim against payer policies.</p>
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

