import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { VerdictCard } from "../components/VerdictCard";
import { Scanner } from "../components/Scanner";
import { clsx } from "clsx";
import { api } from "../api";

interface VerificationResult {
  status: "genuine" | "expired" | "not_found" | "suspicious";
  detail: string;
  drug_name?: string;
  batch_number?: string;
  manufacture_date?: string;
  expiry_date?: string;
}

export function VerificationPage() {
  const { t } = useTranslation();
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const codeInputRef = useRef<HTMLInputElement>(null);

  const verifyCode = async (verificationCode: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.verifyCode(verificationCode) as VerificationResult;
      setResult(data);
    } catch (err) {
      setError(t("common.error"));
      setResult({
        status: "not_found",
        detail: t("common.error"),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim()) {
      verifyCode(code.trim());
    }
  };

  const handleScanResult = (scannedCode: string) => {
    setCode(scannedCode);
    setShowScanner(false);
    verifyCode(scannedCode);
  };

  const handleCloseScanner = () => {
    setShowScanner(false);
  };

  const handleReport = async () => {
    if (!result) return;
    try {
      await api.reportSuspicious(code, "user_reported");
      alert(t("verify.report_sent"));
    } catch {
      alert(t("common.error"));
    }
  };

  useEffect(() => {
    // Auto-focus on load
    codeInputRef.current?.focus();
  }, []);

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-neutral-900">{t("verify.title")}</h1>
          <p className="mt-2 text-neutral-600">{t("verify.subtitle")}</p>
        </div>

        {/* Verdict Card - Always visible once result exists */}
        {result && (
          <VerdictCard
            status={result.status}
            title={t(`verify.${result.status}`)}
            detail={result.detail}
            drugName={result.drug_name}
            batchNumber={result.batch_number}
            manufactureDate={result.manufacture_date}
            expiryDate={result.expiry_date}
            onReport={result.status === "suspicious" || result.status === "not_found" ? handleReport : undefined}
            reportLabel={t("verify.report_suspicious")}
          />
        )}

        {/* Scanner or Manual Entry */}
        {!result || (result.status !== "genuine" && result.status !== "expired") ? (
          <div className="mt-6 space-y-4">
            {/* Scanner Button */}
            <button
              type="button"
              onClick={() => setShowScanner(true)}
              className={clsx(
                "w-full py-4 px-6 rounded-lg font-medium text-lg transition-colors",
                "bg-neutral-100 text-neutral-700 border-2 border-dashed border-neutral-300 hover:bg-neutral-50"
              )}
              aria-label={t("verify.scan_button")}
            >
              <div className="flex items-center justify-center gap-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>{t("verify.scan_button")}</span>
              </div>
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-neutral-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-2 text-neutral-500">{t("verify.manual_entry")}</span>
              </div>
            </div>

            {/* Manual Entry Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="code" className="sr-only">
                  {t("verify.code_placeholder")}
                </label>
                <input
                  ref={codeInputRef}
                  id="code"
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder={t("verify.code_placeholder")}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-lg text-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
                  disabled={loading}
                  autoComplete="off"
                  autoFocus
                />
              </div>

              <button
                type="submit"
                disabled={loading || !code.trim()}
                className={clsx(
                  "w-full py-3 px-6 rounded-lg font-medium text-lg transition-colors",
                  loading
                    ? "bg-genuine-400 text-white cursor-not-allowed"
                    : "bg-genuine-600 text-white hover:bg-genuine-700 focus:ring-2 focus:ring-genuine-500 focus:ring-offset-2"
                )}
              >
                {loading ? t("common.loading") : t("verify.check_button")}
              </button>
            </form>
          </div>
        ) : (
          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setResult(null);
                setCode("");
                codeInputRef.current?.focus();
              }}
              className="text-genuine-600 hover:text-genuine-700 font-medium"
            >
              {t("common.back")}
            </button>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-suspicious-50 border border-suspicious-200 rounded-lg text-suspicious-700 text-sm" role="alert">
            {error}
          </div>
        )}
      </div>

      {/* QR Scanner Modal */}
      {showScanner && (
        <Scanner onScan={handleScanResult} onClose={handleCloseScanner} />
      )}
    </div>
  );
}