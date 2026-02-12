"use client";

import { useRef, useState, useCallback } from "react";

interface Props {
  onRecording: (blob: Blob) => void;
}

export default function AudioRecorder({ onRecording }: Props) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);
  const [recorded, setRecorded] = useState(false);
  const [timer, setTimer] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/wav" });
        onRecording(blob);
        setRecorded(true);
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start();
      setRecording(true);
      setTimer(0);
      timerRef.current = setInterval(() => setTimer((t) => t + 1), 1000);
    } catch {
      alert("Could not access microphone. Please allow microphone access.");
    }
  }, [onRecording]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const reset = () => {
    setRecorded(false);
    setTimer(0);
  };

  const phrase = "The quick brown fox jumps over the lazy dog";

  return (
    <div className="space-y-4">
      <div className="bg-[#0d0520] border border-[#2d1b69] rounded-xl p-4 text-center">
        <p className="text-xs text-[#999] mb-2 uppercase tracking-wider">Please read this aloud</p>
        <p className="text-lg text-white font-medium">&ldquo;{phrase}&rdquo;</p>
      </div>

      {recorded ? (
        <div className="bg-[#0d2e1a] border border-[#166534] rounded-xl p-4 text-center">
          <div className="text-2xl mb-2">&#9989;</div>
          <p className="text-[#4ade80] font-medium">Voice sample recorded ({timer}s)</p>
          <button onClick={reset} className="text-xs text-[#666] hover:text-white mt-2 underline">
            Record again
          </button>
        </div>
      ) : recording ? (
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            <span className="text-red-400 text-sm font-medium">Recording... {timer}s</span>
          </div>
          <button
            onClick={stopRecording}
            className="bg-red-500/20 text-red-400 border border-red-500/30 px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-red-500/30 transition"
          >
            Stop Recording
          </button>
        </div>
      ) : (
        <div className="text-center">
          <button
            onClick={startRecording}
            className="gradient-bg text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition"
          >
            🎤 Start Recording
          </button>
          <p className="text-xs text-[#666] mt-2">Record 5-10 seconds of speech</p>
        </div>
      )}
    </div>
  );
}
