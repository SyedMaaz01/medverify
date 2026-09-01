import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { clsx } from "clsx";
import { api } from "../api";

interface Flag {
  id: string;
  batch_id: string;
  reason: string;
  created_at: string;
  resolved: boolean;
}

interface Batch {
  id: string;
  drug_name: string;
  batch_number: string;
  manufacturer_name: string;
  draper_reg_no: string;
  manufacture_date: string;
  expiry_date: string;
  signed_code: string;
  scan_count: number;
}

interface SuspiciousItem {
  code: string;
  scan_count: number;
  locations: string[];
  reason: string;
}

interface Scan {
  id: string;
  code: string;
  timestamp: string;
  ip_address: string | null;
  approx_location: string | null;
  result: string;
}

export function AdminDashboard() {
  const { t } = useTranslation();
  const [flags, setFlags] = useState<Flag[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [suspicious, setSuspicious] = useState<SuspiciousItem[]>([]);
  const [activeTab, setActiveTab] = useState<"flags" | "batches" | "suspicious">("flags");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBatchScans, setSelectedBatchScans] = useState<Scan[] | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [flagsData, batchesData, suspiciousData] = await Promise.all([
        api.getAdminFlags(),
        api.getAdminBatches(),
        api.getAdminSuspicious(),
      ]);
      setFlags(flagsData);
      setBatches(batchesData);
      setSuspicious(suspiciousData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const fetchBatchScans = useCallback(async (batchId: string) => {
    try {
      const data = await api.getAdminBatchScans(batchId);
      setSelectedBatchScans(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    }
  }, [t]);

  const handleResolveFlag = useCallback(async (flagId: string) => {
    try {
      await api.resolveAdminFlag(flagId);
      setFlags((prev) =>
        prev.map((f) => (f.id === flagId ? { ...f, resolved: true } : f))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    }
  }, [t]);

  useEffect(() => {
    const token = localStorage.getItem("medverify_token");
    if (!token) {
      navigate("/manufacturer", { replace: true });
      return;
    }
    api.getProfile()
      .then((profile) => {
        if (profile.role !== "admin" && profile.role !== "super_admin") {
          setUnauthorized(true);
          return;
        }
        fetchData();
      })
      .catch(() => {
        localStorage.removeItem("medverify_token");
        navigate("/manufacturer", { replace: true });
      });
  }, [navigate, fetchData]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-[calc(100vh-200px)] px-4 py-8">
      <div className="max-w-6xl mx-auto">
        {unauthorized ? (
          <div className="text-center py-16">
            <svg className="mx-auto h-16 w-16 text-suspicious-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v2m0-2h2m-2 0H10m4-6V9a4 4 0 00-8 0v2" />
            </svg>
            <h2 className="mt-4 text-xl font-bold text-neutral-900">Access Denied</h2>
            <p className="mt-2 text-neutral-600">You do not have permission to view this page.</p>
            <button
              onClick={() => navigate("/manufacturer", { replace: true })}
              className="mt-6 px-6 py-2 bg-genuine-600 text-white rounded-lg font-medium hover:bg-genuine-700"
            >
              Go to Manufacturer
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">{t("admin.title")}</h1>
                <p className="text-neutral-600">Monitor suspicious activity and manage batches</p>
              </div>
              <button
                onClick={fetchData}
                disabled={loading}
                className="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg font-medium hover:bg-neutral-50 disabled:opacity-50"
              >
                {loading ? t("common.loading") : "Refresh"}
              </button>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-suspicious-50 border border-suspicious-200 rounded-lg text-suspicious-700" role="alert">
                {error}
              </div>
            )}

            <div className="bg-white rounded-2xl shadow-lg border border-neutral-200 overflow-hidden">
              <div className="border-b border-neutral-200 overflow-x-auto">
                <nav className="flex -mb-px min-w-max" aria-label="Admin tabs">
                  <button
                    onClick={() => setActiveTab("flags")}
                    className={clsx(
                      "px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                      activeTab === "flags"
                        ? "border-genuine-500 text-genuine-600"
                        : "border-transparent text-neutral-500 hover:text-neutral-700"
                    )}
                  >
                    {t("admin.flags")} ({flags.length})
                  </button>
                  <button
                    onClick={() => setActiveTab("suspicious")}
                    className={clsx(
                      "px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                      activeTab === "suspicious"
                        ? "border-genuine-500 text-genuine-600"
                        : "border-transparent text-neutral-500 hover:text-neutral-700"
                    )}
                  >
                    {t("admin.suspicious")} ({suspicious.length})
                  </button>
                  <button
                    onClick={() => setActiveTab("batches")}
                    className={clsx(
                      "px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                      activeTab === "batches"
                        ? "border-genuine-500 text-genuine-600"
                        : "border-transparent text-neutral-500 hover:text-neutral-700"
                    )}
                  >
                    {t("admin.batches")} ({batches.length})
                  </button>
                </nav>
              </div>

              <div className="p-6">
                {activeTab === "flags" && (
                  <FlagsTab flags={flags} onResolve={handleResolveFlag} formatDate={formatDate} />
                )}
                {activeTab === "suspicious" && (
                  <SuspiciousTab suspicious={suspicious} formatDate={formatDate} />
                )}
                {activeTab === "batches" && (
                  <BatchesTab batches={batches} onViewScans={fetchBatchScans} formatDate={formatDate} />
                )}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Batch Scans Modal */}
      {selectedBatchScans !== null && (
        <ScansModal scans={selectedBatchScans} onClose={() => setSelectedBatchScans(null)} formatDate={formatDate} />
      )}
    </div>
  );
}

function FlagsTab({
  flags,
  onResolve,
  formatDate,
}: {
  flags: Flag[];
  onResolve: (id: string) => void;
  formatDate: (date: string) => string;
}) {
  const { t } = useTranslation();

  if (flags.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-2 text-lg font-medium text-neutral-900">{t("admin.no_flags")}</h3>
        <p className="mt-1 text-neutral-500">No suspicious activity detected</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-neutral-500 border-b border-neutral-200">
            <th className="pb-3 font-medium">{t("admin.flag_reason")}</th>
            <th className="pb-3 font-medium">{t("admin.flag_created")}</th>
            <th className="pb-3 font-medium">Batch ID</th>
            <th className="pb-3 font-medium">{t("admin.flag_resolve")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200">
          {flags.map((flag) => (
            <tr key={flag.id} className={clsx("hover:bg-neutral-50", flag.resolved && "bg-genuine-50")}>
              <td className="py-4">
                <div className="font-medium text-neutral-900">{flag.reason}</div>
                <div className="text-sm text-neutral-500">Batch: {flag.batch_id.slice(0, 8)}...</div>
              </td>
              <td className="py-4 text-neutral-700 whitespace-nowrap">{formatDate(flag.created_at)}</td>
              <td className="py-4 text-neutral-700 font-mono text-sm">{flag.batch_id}</td>
              <td className="py-4">
                {flag.resolved ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-genuine-100 text-genuine-800">
                    {t("admin.flag_resolved")}
                  </span>
                ) : (
                  <button
                    onClick={() => onResolve(flag.id)}
                    className="px-3 py-1.5 text-sm font-medium text-genuine-600 hover:text-genuine-700 bg-genuine-50 rounded-lg"
                  >
                    {t("admin.flag_resolve")}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SuspiciousTab({
  suspicious,
  formatDate: _formatDate,
}: {
  suspicious: SuspiciousItem[];
  formatDate: (date: string) => string;
}) {
  const { t } = useTranslation();

  if (suspicious.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="mt-2 text-lg font-medium text-neutral-900">No suspicious patterns</h3>
        <p className="mt-1 text-neutral-500">No codes exceeded the scan threshold</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-neutral-500 border-b border-neutral-200">
            <th className="pb-3 font-medium">{t("admin.flag_reason")}</th>
            <th className="pb-3 font-medium">{t("admin.flag_count")}</th>
            <th className="pb-3 font-medium">{t("admin.flag_locations")}</th>
            <th className="pb-3 font-medium">Code</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200">
          {suspicious.map((item, index) => (
            <tr key={index} className="hover:bg-suspicious-50">
              <td className="py-4 text-suspicious-700 font-medium">{item.reason}</td>
              <td className="py-4 text-neutral-700 font-bold">{item.scan_count}</td>
              <td className="py-4 text-neutral-700">
                <div className="flex flex-wrap gap-1">
                  {item.locations.map((loc, i) => (
                    <span key={i} className="px-2 py-0.5 text-xs bg-neutral-100 text-neutral-600 rounded">
                      {loc}
                    </span>
                  ))}
                </div>
              </td>
              <td className="py-4 font-mono text-sm text-neutral-700">{item.code}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BatchesTab({
  batches,
  onViewScans,
  formatDate: _formatDate,
}: {
  batches: Batch[];
  onViewScans: (batchId: string) => void;
  formatDate: (date: string) => string;
}) {
  const { t } = useTranslation();

  if (batches.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        <h3 className="mt-2 text-lg font-medium text-neutral-900">No batches registered</h3>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-neutral-500 border-b border-neutral-200">
            <th className="pb-3 font-medium">{t("verify.drug_name")}</th>
            <th className="pb-3 font-medium">{t("verify.batch_number")}</th>
            <th className="pb-3 font-medium">{t("verify.manufacturer")}</th>
            <th className="pb-3 font-medium">{t("verify.manufacture_date")}</th>
            <th className="pb-3 font-medium">{t("verify.expiry_date")}</th>
            <th className="pb-3 font-medium">Scans</th>
            <th className="pb-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200">
          {batches.map((batch) => (
            <tr key={batch.id} className="hover:bg-neutral-50">
              <td className="py-4 font-medium text-neutral-900">{batch.drug_name}</td>
              <td className="py-4 text-neutral-700 font-mono">{batch.batch_number}</td>
              <td className="py-4 text-neutral-700">{batch.manufacturer_name}</td>
              <td className="py-4 text-neutral-700">{batch.manufacture_date}</td>
              <td className="py-4 text-neutral-700">{batch.expiry_date}</td>
              <td className="py-4 text-neutral-700 font-medium">{batch.scan_count}</td>
              <td className="py-4">
                <button
                  onClick={() => onViewScans(batch.id)}
                  className="text-genuine-600 hover:text-genuine-700 font-medium"
                >
                  View Scans
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScansModal({
  scans,
  onClose,
  formatDate,
}: {
  scans: Scan[];
  onClose: () => void;
  formatDate: (date: string) => string;
}) {
  const { t } = useTranslation();

  const resultColors: Record<string, string> = {
    genuine: "bg-genuine-100 text-genuine-800",
    expired: "bg-expired-100 text-expired-800",
    not_found: "bg-suspicious-100 text-suspicious-800",
    suspicious: "bg-suspicious-100 text-suspicious-800",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="w-full max-w-4xl max-h-[80vh] bg-white rounded-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-neutral-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-900">{t("admin.scans")} ({scans.length})</h2>
          <button onClick={onClose} className="p-2 text-neutral-500 hover:text-neutral-700 rounded-lg hover:bg-neutral-100">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[60vh]">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-neutral-500 border-b border-neutral-200">
                  <th className="pb-3 font-medium">{t("admin.flag_created")}</th>
                  <th className="pb-3 font-medium">Code</th>
                  <th className="pb-3 font-medium">IP Address</th>
                  <th className="pb-3 font-medium">Location</th>
                  <th className="pb-3 font-medium">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {scans.map((scan) => (
                  <tr key={scan.id} className="hover:bg-neutral-50">
                    <td className="py-3 text-neutral-700 whitespace-nowrap">{formatDate(scan.timestamp)}</td>
                    <td className="py-3 font-mono text-sm text-neutral-700">{scan.code}</td>
                    <td className="py-3 text-neutral-700">{scan.ip_address || "-"}</td>
                    <td className="py-3 text-neutral-700">{scan.approx_location || "-"}</td>
                    <td className="py-3">
                      <span className={clsx("inline-flex px-2 py-1 text-xs font-medium rounded-full", resultColors[scan.result])}>
                        {scan.result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="p-4 border-t border-neutral-200 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg font-medium hover:bg-neutral-50">
            {t("common.close")}
          </button>
        </div>
      </div>
    </div>
  );
}