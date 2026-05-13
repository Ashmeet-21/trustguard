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
    <div className="space-y-4">
      {captured ? (
        <div className="relative">
          <img
            src={captured}
            alt="Captured"
            className="w-full rounded-xl border border-[#222]"
          />
          <button
            onClick={retake}
            className="absolute top-2 right-2 bg-[#222] hover:bg-[#333] text-white rounded-lg px-3 py-1 text-xs"
          >
            Retake
          </button>
        </div>
      ) : streaming ? (
        <div className="relative">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full rounded-xl border border-[#222]"
            style={{ transform: "scaleX(-1)" }}
          />
          {/* Face oval guide overlay */}
          <div className="absolute inset-0 pointer-events-none rounded-xl overflow-hidden">
            <svg className="w-full h-full" viewBox="0 0 640 480" preserveAspectRatio="xMidYMid slice">
              <defs>
                <mask id="faceOvalMask">
                  <rect width="640" height="480" fill="white" />
                  <ellipse cx="320" cy="220" rx="140" ry="180" fill="black" />
                </mask>
              </defs>
              <rect width="640" height="480" fill="rgba(0,0,0,0.35)" mask="url(#faceOvalMask)" />
              <ellipse cx="320" cy="220" rx="140" ry="180" fill="none" stroke="#00d4ff" strokeWidth="2.5" strokeDasharray="10 5" />
            </svg>
            <p className="absolute bottom-16 left-0 right-0 text-center text-xs text-white/90 font-medium drop-shadow-lg">
              Position your full face within the oval
            </p>
          </div>
          <button
            onClick={takeSnapshot}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 gradient-bg text-white rounded-full w-14 h-14 flex items-center justify-center text-2xl hover:opacity-90 transition shadow-lg"
          >
            &#128247;
          </button>
        </div>
      ) : (
        <div className="border-2 border-dashed border-[#333] rounded-xl p-8 text-center">
          <div className="text-4xl mb-3">📷</div>
          <p className="text-[#666] text-sm mb-1">
            Take a selfie or upload a photo
          </p>
          <p className="text-[#555] text-xs mb-4">
            Make sure your full face is visible — no half face or cropped photos
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3 mb-4 text-xs">
              {error}
            </div>
          )}

          <div className="flex gap-3 justify-center">
            <button
              onClick={startCamera}
              disabled={loading}
              className="gradient-bg text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? "Opening Camera..." : "Open Camera"}
            </button>
            <label className="bg-[#1a1a1a] text-white px-5 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-[#222] transition border border-[#333]">
              Upload File
              <input
                type="file"
                accept="image/jpeg,image/png"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>
      )}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
