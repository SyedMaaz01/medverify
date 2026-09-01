import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";
import { api } from "../api";

interface Batch {
  id: string;
  drug_name: string;
  batch_number: string;
  manufacture_date: string;
  expiry_date: string;
  signed_code: string;
  draper_reg_no: string;
  created_at: string;
  scan_count?: number;
}

interface Manufacturer {
  id: string;
  name: string;
  drap_license_no: string;
  contact_email?: string;
  contact_phone?: string;
}

export function ManufacturerPage() {
  const { t } = useTranslation();
  const [manufacturer, setManufacturer] = useState<Manufacturer | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"login" | "batches" | "register">("login");

  // Login form state
  const [loginLicense, setLoginLicense] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register batch form state
  const [regDrugName, setRegDrugName] = useState("");
  const [regBatchNumber, setRegBatchNumber] = useState("");
  const [regManufactureDate, setRegManufactureDate] = useState("");
  const [regExpiryDate, setRegExpiryDate] = useState("");
  const [regDraperRegNo, setRegDraperRegNo] = useState("");
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);
  const [regSuccess, setRegSuccess] = useState(false);

  // Fetch batches after login
  const fetchBatches = async () => {
    try {
      const data = await api.listBatches();
      setBatches(data.items || data);
    } catch {
      setError(t("common.error"));
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(loginLicense, loginPassword);
      localStorage.setItem("medverify_token", data.access_token);
      setManufacturer(data.manufacturer);
      setActiveTab("batches");
      await fetchBatches();
    } catch (err: any) {
      setError(err.message || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("medverify_token");
    setManufacturer(null);
    setBatches([]);
    setActiveTab("login");
  };

  const handleRegisterBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manufacturer) return;

    setRegLoading(true);
    setRegError(null);
    setRegSuccess(false);

    // Validate dates
    if (new Date(regManufactureDate) >= new Date(regExpiryDate)) {
      setRegError("Expiry date must be after manufacture date");
      setRegLoading(false);
      return;
    }

    try {
      const data = await api.registerBatch({
        manufacturer_id: manufacturer.id,
        drug_name: regDrugName,
        manufacturer_name: manufacturer.name,
        draper_reg_no: regDraperRegNo,
        batch_number: regBatchNumber,
        manufacture_date: regManufactureDate,
        expiry_date: regExpiryDate,
      });
      setRegSuccess(true);
      setQrCode(`https://medverify.app/verify/${data.signed_code}`);
      // Reset form
      setRegDrugName("");
      setRegBatchNumber("");
      setRegManufactureDate("");
      setRegExpiryDate("");
      setRegDraperRegNo("");
      await fetchBatches();
    } catch (err: any) {
      setRegError(err.message || t("common.error"));
    } finally {
      setRegLoading(false);
    }
  };

  const downloadQR = async () => {
    if (!qrCode) return;
    try {
      const response = await api.getQrCode(qrCode);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `qr-${regBatchNumber}.png`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      alert(t("common.error"));
    }
  };

  // Check for existing session
  useEffect(() => {
    const token = localStorage.getItem("medverify_token");
    if (token) {
      api.getProfile()
        .then((data) => {
          setManufacturer(data);
          setActiveTab("batches");
          fetchBatches();
        })
        .catch(() => {
          localStorage.removeItem("medverify_token");
        });
    }
  }, []);

  if (activeTab === "login") {
    return (
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-lg border border-neutral-200 p-8">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-neutral-900">{t("mfr.title")}</h1>
              <p className="mt-2 text-neutral-600">{t("mfr.login")}</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              <div>
                <label htmlFor="license" className="block text-sm font-medium text-neutral-700 mb-2">
                  {t("mfr.drap_license")}
                </label>
                <input
                  id="license"
                  type="text"
                  value={loginLicense}
                  onChange={(e) => setLoginLicense(e.target.value)}
                  placeholder={t("mfr.drap_license")}
                  className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-neutral-700 mb-2">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
                  required
                />
              </div>

              {error && (
                <div className="p-4 bg-suspicious-50 border border-suspicious-200 rounded-lg text-suspicious-700 text-sm" role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className={clsx(
                  "w-full py-3 px-6 rounded-lg font-medium text-lg transition-colors",
                  loading
                    ? "bg-genuine-400 text-white cursor-not-allowed"
                    : "bg-genuine-600 text-white hover:bg-genuine-700 focus:ring-2 focus:ring-genuine-500 focus:ring-offset-2"
                )}
              >
                {loading ? t("common.loading") : t("mfr.login")}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-200px)] px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">{t("mfr.title")}</h1>
            <p className="text-neutral-600">{manufacturer?.name} • {manufacturer?.drap_license_no}</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-neutral-600 hover:text-neutral-900 font-medium"
          >
            {t("common.logout") || "Logout"}
          </button>
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-neutral-200 overflow-hidden">
          <div className="border-b border-neutral-200">
            <nav className="flex -mb-px" aria-label="Tabs">
              <button
                onClick={() => setActiveTab("batches")}
                className={clsx(
                  "px-6 py-3 text-sm font-medium border-b-2 transition-colors",
                  activeTab === "batches"
                    ? "border-genuine-500 text-genuine-600"
                    : "border-transparent text-neutral-500 hover:text-neutral-700"
                )}
              >
                {t("mfr.batches_list")}
              </button>
              <button
                onClick={() => setActiveTab("register")}
                className={clsx(
                  "px-6 py-3 text-sm font-medium border-b-2 transition-colors",
                  activeTab === "register"
                    ? "border-genuine-500 text-genuine-600"
                    : "border-transparent text-neutral-500 hover:text-neutral-700"
                )}
              >
                {t("mfr.register_batch")}
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === "batches" && (
              <BatchList batches={batches} onRefresh={fetchBatches} />
            )}
            {activeTab === "register" && (
              <BatchRegistrationForm
                manufacturer={manufacturer!}
                onSubmit={handleRegisterBatch}
                loading={regLoading}
                error={regError}
                success={regSuccess}
                qrCode={qrCode}
                onDownload={downloadQR}
                formData={{
                  drugName: regDrugName,
                  batchNumber: regBatchNumber,
                  manufactureDate: regManufactureDate,
                  expiryDate: regExpiryDate,
                  draperRegNo: regDraperRegNo,
                }}
                onChange={{
                  drugName: setRegDrugName,
                  batchNumber: setRegBatchNumber,
                  manufactureDate: setRegManufactureDate,
                  expiryDate: setRegExpiryDate,
                  draperRegNo: setRegDraperRegNo,
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function BatchList({ batches, onRefresh: _onRefresh }: { batches: Batch[]; onRefresh?: () => void }) {
  const { t } = useTranslation();

  if (batches.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        <h3 className="mt-2 text-lg font-medium text-neutral-900">No batches yet</h3>
        <p className="mt-1 text-neutral-500">Register your first batch to get started</p>
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
            <th className="pb-3 font-medium">{t("verify.manufacture_date")}</th>
            <th className="pb-3 font-medium">{t("verify.expiry_date")}</th>
            <th className="pb-3 font-medium">{t("verify.draper_reg_no")}</th>
            <th className="pb-3 font-medium">Scans</th>
            <th className="pb-3 font-medium">QR Code</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200">
          {batches.map((batch) => (
            <tr key={batch.id} className="hover:bg-neutral-50">
              <td className="py-4 font-medium text-neutral-900">{batch.drug_name}</td>
              <td className="py-4 text-neutral-700 font-mono">{batch.batch_number}</td>
              <td className="py-4 text-neutral-700">{batch.manufacture_date}</td>
              <td className="py-4 text-neutral-700">{batch.expiry_date}</td>
              <td className="py-4 text-neutral-700">{batch.draper_reg_no}</td>
              <td className="py-4 text-neutral-700">{batch.scan_count || 0}</td>
              <td className="py-4">
                <a
                  href={`/api/qr?url=${encodeURIComponent(`https://medverify.app/verify/${batch.signed_code}`)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-genuine-600 hover:text-genuine-700 font-medium"
                >
                  Download QR
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BatchRegistrationForm({
  manufacturer: _manufacturer,
  onSubmit,
  loading,
  error,
  success,
  qrCode,
  onDownload,
  formData,
  onChange,
}: {
  manufacturer: Manufacturer;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
  error: string | null;
  success: boolean;
  qrCode: string | null;
  onDownload: () => void;
  formData: {
    drugName: string;
    batchNumber: string;
    manufactureDate: string;
    expiryDate: string;
    draperRegNo: string;
  };
  onChange: {
    drugName: (v: string) => void;
    batchNumber: (v: string) => void;
    manufactureDate: (v: string) => void;
    expiryDate: (v: string) => void;
    draperRegNo: (v: string) => void;
  };
}) {
  const { t } = useTranslation();

  const today = new Date().toISOString().split("T")[0];

  return (
    <form onSubmit={onSubmit} className="space-y-6 max-w-2xl">
      {success && qrCode && (
        <div className="bg-genuine-50 border border-genuine-200 rounded-lg p-6 text-center animate-fade-in">
          <svg className="mx-auto h-12 w-12 text-genuine-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mt-3 text-lg font-semibold text-genuine-800">{t("mfr.qr_generated")}</h3>
          <p className="mt-1 text-genuine-700">Batch <code className="bg-white px-2 py-0.5 rounded">{formData.batchNumber}</code> registered</p>
          <div className="mt-4 flex justify-center gap-3">
            <button
              type="button"
              onClick={onDownload}
              className="px-4 py-2 bg-genuine-600 text-white rounded-lg font-medium hover:bg-genuine-700"
            >
              {t("mfr.download_qr")}
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg font-medium hover:bg-neutral-50"
            >
              Register Another
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-suspicious-50 border border-suspicious-200 rounded-lg text-suspicious-700 text-sm" role="alert">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="drug_name" className="block text-sm font-medium text-neutral-700 mb-2">
            {t("mfr.drug_name")} *
          </label>
          <input
            id="drug_name"
            type="text"
            value={formData.drugName}
            onChange={(e) => onChange.drugName(e.target.value)}
            required
            className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
            disabled={loading || success}
          />
        </div>

        <div>
          <label htmlFor="batch_number" className="block text-sm font-medium text-neutral-700 mb-2">
            {t("mfr.batch_number")} *
          </label>
          <input
            id="batch_number"
            type="text"
            value={formData.batchNumber}
            onChange={(e) => onChange.batchNumber(e.target.value)}
            required
            className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
            disabled={loading || success}
          />
        </div>

        <div>
          <label htmlFor="manufacture_date" className="block text-sm font-medium text-neutral-700 mb-2">
            {t("mfr.manufacture_date")} *
          </label>
          <input
            id="manufacture_date"
            type="date"
            value={formData.manufactureDate}
            onChange={(e) => onChange.manufactureDate(e.target.value)}
            max={today}
            required
            className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
            disabled={loading || success}
          />
        </div>

        <div>
          <label htmlFor="expiry_date" className="block text-sm font-medium text-neutral-700 mb-2">
            {t("mfr.expiry_date")} *
          </label>
          <input
            id="expiry_date"
            type="date"
            value={formData.expiryDate}
            onChange={(e) => onChange.expiryDate(e.target.value)}
            min={formData.manufactureDate || today}
            required
            className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
            disabled={loading || success}
          />
        </div>

        <div className="md:col-span-2">
          <label htmlFor="draper_reg_no" className="block text-sm font-medium text-neutral-700 mb-2">
            {t("mfr.draper_reg_no")} *
          </label>
          <input
            id="draper_reg_no"
            type="text"
            value={formData.draperRegNo}
            onChange={(e) => onChange.draperRegNo(e.target.value)}
            required
            className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-genuine-500 focus:border-genuine-500"
            disabled={loading || success}
          />
        </div>
      </div>

      <div className="pt-4 border-t border-neutral-200">
        <button
          type="submit"
          disabled={loading || success}
          className={clsx(
            "w-full py-3 px-6 rounded-lg font-medium text-lg transition-colors",
            loading
              ? "bg-genuine-400 text-white cursor-not-allowed"
              : "bg-genuine-600 text-white hover:bg-genuine-700 focus:ring-2 focus:ring-genuine-500 focus:ring-offset-2"
          )}
        >
          {loading ? t("common.loading") : t("mfr.generate_qr")}
        </button>
      </div>
    </form>
  );
}