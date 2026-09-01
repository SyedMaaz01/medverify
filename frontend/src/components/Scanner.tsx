import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrowserMultiFormatReader, BarcodeFormat } from "@zxing/library";

interface ScannerProps {
  onScan: (code: string) => void;
  onClose: () => void;
}

export function Scanner({ onScan, onClose }: ScannerProps) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(true);
  const readerRef = useRef<BrowserMultiFormatReader | null>(null);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          await videoRef.current.play();
        }
      } catch (err) {
        setError(t("common.error"));
        console.error("Camera access error:", err);
      }
    };

    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (readerRef.current) {
        readerRef.current.reset();
      }
    };
  }, []);

  useEffect(() => {
    if (!scanning || !videoRef.current) return;

    const videoElement = videoRef.current;
    const reader = new BrowserMultiFormatReader();
    readerRef.current = reader;

    const hints = new Map();
    hints.set("TRY_HARDER", true);
    hints.set("POSSIBLE_FORMATS", [BarcodeFormat.QR_CODE]);

    const startScan = async () => {
      try {
        await reader.decodeFromVideoDevice(
          null,
          videoElement,
          (result, err) => {
            if (result) {
              const code = result.getText();
              onScan(code);
              setScanning(false);
            }
            if (err && !(err instanceof Error && err.name === "NotFoundException")) {
              console.warn("QR scan error:", err);
            }
          }
        );
      } catch (err) {
        console.error("Scan error:", err);
      }
    };

    startScan();

    return () => {
      reader.reset();
    };
  }, [scanning, onScan]);

  const handleManualClose = () => {
    setScanning(false);
    if (readerRef.current) {
      readerRef.current.reset();
    }
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="scanner-title"
    >
      <div className="relative w-full max-w-md bg-white rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-neutral-200 flex items-center justify-between">
          <h2 id="scanner-title" className="text-lg font-semibold text-neutral-900">
            {t("verify.scanning")}
          </h2>
          <button
            onClick={handleManualClose}
            className="p-2 text-neutral-500 hover:text-neutral-700 rounded-lg hover:bg-neutral-100"
            aria-label="Close scanner"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="relative aspect-video bg-black">
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            playsInline
            muted
            aria-hidden="true"
          />

          {/* Scanning overlay */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-64 h-64 border-4 border-genuine-500 rounded-lg relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-2 h-2 bg-genuine-500 rounded-full" />
              <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-2 h-2 bg-genuine-500 rounded-full" />
              <div className="absolute -left-4 top-1/2 -translate-y-1/2 w-2 h-2 bg-genuine-500 rounded-full" />
              <div className="absolute -right-4 top-1/2 -translate-y-1/2 w-2 h-2 bg-genuine-500 rounded-full" />
              <div className="absolute inset-0 border-2 border-genuine-500/50 rounded-lg animate-pulse" />
            </div>
          </div>

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/70 p-4">
              <div className="text-center text-white">
                <p className="mb-2">{error}</p>
                <button
                  onClick={handleManualClose}
                  className="px-4 py-2 bg-white text-black rounded-lg font-medium"
                >
                  {t("common.close")}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 bg-neutral-50 border-t border-neutral-200 text-center">
          <p className="text-sm text-neutral-600 mb-3">
            {t("verify.manual_entry")}
          </p>
          <button
            onClick={handleManualClose}
            className="text-genuine-600 hover:text-genuine-700 font-medium"
          >
            {t("common.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}