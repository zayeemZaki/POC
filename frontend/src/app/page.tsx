"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = "http://127.0.0.1:8000";

interface Claim {
  id: number;
  patient_id: string;
  payer_name: string | null;
  date_of_service: string | null;
  claim_amount: number | null;
  status: string;
}

export default function Home() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [filteredClaims, setFilteredClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    async function fetchClaims() {
      try {
        const res = await fetch(`${API}/claims`);
        if (!res.ok) throw new Error(`Failed to fetch claims (${res.status})`);
        const data: Claim[] = await res.json();
        setClaims(data);
        setFilteredClaims(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load claims");
      } finally {
        setLoading(false);
      }
    }
    fetchClaims();
  }, []);

  useEffect(() => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) {
      setFilteredClaims(claims);
      return;
    }
    const filtered = claims.filter(
      (claim) =>
        claim.patient_id.toLowerCase().includes(query) ||
        (claim.payer_name && claim.payer_name.toLowerCase().includes(query))
    );
    setFilteredClaims(filtered);
  }, [searchQuery, claims]);

  function handleRowClick(id: number) {
    router.push(`/claim/${id}`);
  }

  function getStatusText(status: string) {
    const normalized = status.toUpperCase();
    if (normalized === "DENIED") {
      return <span className="font-bold text-black">{normalized}</span>;
    }
    return <span className="text-gray-500">{normalized}</span>;
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <p className="text-sm text-black">LOADING...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-white">
        <p className="text-sm font-bold text-black">ERROR</p>
        <p className="text-sm text-gray-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-black bg-white">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <h1 className="text-lg font-bold text-black uppercase tracking-wide">Claims Worklist</h1>
          <p className="text-xs text-gray-500 mt-1 uppercase tracking-wide">
            Verification Dashboard
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Search Bar */}
        <div className="mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="FILTER BY PATIENT ID OR PAYER"
            className="h-10 w-full max-w-md border border-gray-300 bg-white px-3 text-xs uppercase tracking-wide text-black placeholder:text-gray-400 focus:border-black focus:outline-none"
          />
        </div>

        {/* Claims Table */}
        <div className="border border-gray-300 bg-white">
          <table className="w-full">
            <thead className="bg-gray-100 border-b border-gray-300">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-black">
                  Patient ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-black">
                  Payer
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-black">
                  Date of Service
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-black">
                  Claim Amount
                </th>
                <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-black">
                  Status
                </th>
                <th className="px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-black">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredClaims.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-xs text-gray-500 uppercase">
                    No claims found
                  </td>
                </tr>
              ) : (
                filteredClaims.map((claim) => (
                  <tr
                    key={claim.id}
                    onClick={() => handleRowClick(claim.id)}
                    className="cursor-pointer border-b border-gray-200 transition-colors hover:bg-gray-100"
                  >
                    <td className="px-4 py-3 text-xs font-medium text-black">
                      {claim.patient_id}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">
                      {claim.payer_name || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">
                      {claim.date_of_service || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-black">
                      {claim.claim_amount != null
                        ? `$${claim.claim_amount.toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {getStatusText(claim.status)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(claim.id);
                        }}
                        className="text-xs text-black underline hover:text-gray-600"
                      >
                        VIEW
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Results count */}
        <div className="mt-4 text-xs text-gray-500 uppercase tracking-wide">
          Showing {filteredClaims.length} of {claims.length} records
        </div>
      </main>
    </div>
  );
}
