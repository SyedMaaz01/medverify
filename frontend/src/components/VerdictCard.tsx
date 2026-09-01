import { clsx } from "clsx";

interface VerdictCardProps {
  status: "genuine" | "expired" | "not_found" | "suspicious";
  title: string;
  detail: string;
  drugName?: string;
  batchNumber?: string;
  manufactureDate?: string;
  expiryDate?: string;
  onReport?: () => void;
  reportLabel?: string;
}

const statusStyles: Record<string, { bg: string; border: string; text: string; iconBg: string }> = {
  genuine: {
    bg: "bg-genuine-50",
    border: "border-genuine-200",
    text: "text-genuine-800",
    iconBg: "bg-genuine-100",
  },
  expired: {
    bg: "bg-expired-50",
    border: "border-expired-200",
    text: "text-expired-800",
    iconBg: "bg-expired-100",
  },
  suspicious: {
    bg: "bg-suspicious-50",
    border: "border-suspicious-200",
    text: "text-suspicious-800",
    iconBg: "bg-suspicious-100",
  },
  not_found: {
    bg: "bg-suspicious-50",
    border: "border-suspicious-200",
    text: "text-suspicious-800",
    iconBg: "bg-suspicious-100",
  },
};

const statusIcons: Record<string, React.ReactNode> = {
  genuine: (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  expired: (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  suspicious: (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  not_found: (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
};

export function VerdictCard({
  status,
  title,
  detail,
  drugName,
  batchNumber,
  manufactureDate,
  expiryDate,
  onReport,
  reportLabel,
}: VerdictCardProps) {
  const styles = statusStyles[status] || statusStyles.not_found;

  return (
    <div
      className={clsx(
        "rounded-2xl p-6 shadow-lg border-2 animate-fade-in",
        styles.bg,
        styles.border
      )}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-4">
        <div
          className={clsx(
            "flex-shrink-0 w-16 h-16 rounded-full flex items-center justify-center",
            styles.iconBg,
            styles.text
          )}
          aria-hidden="true"
        >
          {statusIcons[status]}
        </div>

        <div className="flex-1 min-w-0">
          <h2 className={clsx("text-2xl font-bold", styles.text)}>
            {title}
          </h2>
          <p className={clsx("mt-1 text-lg", styles.text)}>{detail}</p>
        </div>
      </div>

      {/* Details - only show for genuine/expired */}
      {(status === "genuine" || status === "expired") && (
        <div className="mt-6 pt-6 border-t border-neutral-200 space-y-3">
          {drugName && (
            <div className="flex justify-between text-sm">
              <span className="text-neutral-500">Drug Name</span>
              <span className="font-medium text-neutral-900">{drugName}</span>
            </div>
          )}
          {batchNumber && (
            <div className="flex justify-between text-sm">
              <span className="text-neutral-500">Batch Number</span>
              <span className="font-medium text-neutral-900 font-mono">{batchNumber}</span>
            </div>
          )}
          {manufactureDate && (
            <div className="flex justify-between text-sm">
              <span className="text-neutral-500">Manufacture Date</span>
              <span className="font-medium text-neutral-900">{manufactureDate}</span>
            </div>
          )}
          {expiryDate && (
            <div className="flex justify-between text-sm">
              <span className="text-neutral-500">Expiry Date</span>
              <span className="font-medium text-neutral-900">{expiryDate}</span>
            </div>
          )}
        </div>
      )}

      {/* Report button for suspicious/not_found */}
      {onReport && (
        <div className="mt-6 pt-6 border-t border-neutral-200">
          <button
            onClick={onReport}
            className={clsx(
              "w-full py-3 px-4 rounded-lg font-medium text-base transition-colors",
              "bg-suspicious-50 text-suspicious-700 border border-suspicious-200 hover:bg-suspicious-100"
            )}
          >
            {reportLabel}
          </button>
        </div>
      )}
    </div>
  );
}