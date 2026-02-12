"use client";

import { useRef, useState, useCallback } from "react";

interface Props {
  onCapture: (file: File) => void;
}

export default function CameraCapture({ onCapture }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [captured, setCaptured] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setStreaming(true);
      setCaptured(null);
    } catch {
      alert("Could not access camera. Please allow camera access or upload a file.");
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
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], "selfie.jpg", { type: "image/jpeg" });
        onCapture(file);
        setCaptured(canvas.toDataURL("image/jpeg"));
        stopCamera();
      }
    }, "image/jpeg", 0.9);
  }, [onCapture, stopCamera]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    onCapture(file);
    const reader = new FileReader();
    reader.onload = (ev) => setCaptured(ev.target?.result as string);
    reader.readAsDataURL(file);
  };

  return (
    <div className="space-y-4">
      {captured ? (
        <div className="relative">
          <img src={captured} alt="Captured" className="w-full rounded-xl border border-[#222]" />
          <button
            onClick={() => { setCaptured(null); }}
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
            className="w-full rounded-xl border border-[#222] mirror"
            style={{ transform: "scaleX(-1)" }}
          />
          <button
            onClick={takeSnapshot}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 gradient-bg text-white rounded-full w-14 h-14 flex items-center justify-center text-2xl hover:opacity-90 transition"
          >
            &#128247;
          </button>
        </div>
      ) : (
        <div className="border-2 border-dashed border-[#333] rounded-xl p-8 text-center">
          <div className="text-4xl mb-3">📷</div>
          <p className="text-[#666] text-sm mb-4">Take a selfie or upload a photo</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={startCamera}
              className="gradient-bg text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition"
            >
              Open Camera
            </button>
            <label className="bg-[#1a1a1a] text-white px-5 py-2.5 rounded-lg text-sm font-medium cursor-pointer hover:bg-[#222] transition border border-[#333]">
              Upload File
              <input type="file" accept="image/jpeg,image/png" onChange={handleFileUpload} className="hidden" />
            </label>
          </div>
        </div>
      )}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
