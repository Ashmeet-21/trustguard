"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface Props {
  onCapture: (file: File) => void;
  onReset?: () => void;
}

export default function CameraCapture({ onCapture, onReset }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [captured, setCaptured] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Attach the stream to the video element AFTER it renders
  useEffect(() => {
    if (streaming && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [streaming]);

  // Cleanup camera on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  const startCamera = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
      });
      streamRef.current = stream;
      // Set streaming=true first so the <video> element renders,
      // then useEffect above will attach the stream to it
      setStreaming(true);
      setCaptured(null);
    } catch (err) {
      const msg =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Camera permission denied. Please allow camera access in your browser settings."
          : err instanceof DOMException && err.name === "NotFoundError"
          ? "No camera found. Please connect a camera or use the Upload option."
          : "Could not access camera. Please try uploading a photo instead.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setStreaming(false);
  }, []);

  const takeSnapshot = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const video = videoRef.current;

    // Ensure video has dimensions
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Mirror the snapshot to match the mirrored preview
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], "selfie.jpg", { type: "image/jpeg" });
          setCaptured(canvas.toDataURL("image/jpeg"));
          stopCamera();
          onCapture(file);
        }
      },
      "image/jpeg",
      0.9
    );
  }, [onCapture, stopCamera]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    const reader = new FileReader();
    reader.onload = (ev) => setCaptured(ev.target?.result as string);
    reader.readAsDataURL(file);
    onCapture(file);
  };

  const retake = () => {
    setCaptured(null);
    setError(null);
    onReset?.();
  };

  return (
    <div>
      {captured ? (
        <div className="flex flex-col sm:flex-row gap-5 items-start">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={captured}
            alt="Your selfie"
            className="w-full sm:w-64 aspect-[4/3] object-cover rounded-[4px] border border-rule"
          />
          <button onClick={retake} className="btn btn-quiet">
            Take a different photo
          </button>
        </div>
      ) : streaming ? (
        <div>
          <div className="relative rounded-[4px] overflow-hidden border border-rule bg-ink">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full block"
              style={{ transform: "scaleX(-1)" }}
            />
            {/* Face guide: everything outside the oval is dimmed */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 640 480" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
              <defs>
                <mask id="faceOvalMask">
                  <rect width="640" height="480" fill="white" />
                  <ellipse cx="320" cy="225" rx="140" ry="180" fill="black" />
                </mask>
              </defs>
              <rect width="640" height="480" fill="rgba(22,35,58,0.45)" mask="url(#faceOvalMask)" />
              <ellipse cx="320" cy="225" rx="140" ry="180" fill="none" stroke="#f9faf8" strokeWidth="2" />
            </svg>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button onClick={takeSnapshot} className="btn">Take photo</button>
            <button onClick={stopCamera} className="btn btn-quiet">Cancel</button>
            <p className="text-sm text-ink-faint">Fit your whole face inside the oval.</p>
          </div>
        </div>
      ) : (
        <div className="border border-dashed border-rule-strong rounded-[4px] bg-paper/60 px-6 py-10 text-center">
          <svg className="mx-auto text-ink-faint" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" />
            <circle cx="12" cy="10" r="3" />
            <path d="M7 17c.8-2.2 2.7-3.3 5-3.3s4.2 1.1 5 3.3" />
          </svg>
          <p className="mt-3 text-ink font-medium">Your whole face, well lit, looking at the camera</p>
          <p className="mt-1 text-sm text-ink-faint">No sunglasses, no cropped or half-face photos.</p>

          {error && (
            <p className="note note-fail mt-5 text-left" role="alert"><span>{error}</span></p>
          )}

          <div className="mt-6 flex flex-wrap gap-3 justify-center">
            <button onClick={startCamera} disabled={loading} className="btn">
              {loading ? "Opening camera…" : "Open camera"}
            </button>
            <label className="btn btn-quiet focus-within:outline focus-within:outline-2 focus-within:outline-seal">
              Upload a photo
              <input type="file" accept="image/jpeg,image/png" onChange={handleFileUpload} className="sr-only" />
            </label>
          </div>
        </div>
      )}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
