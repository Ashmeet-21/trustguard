"use client";

import { useRef, useState, useCallback } from "react";
import { MIN_RECORDING_SECONDS, checkRecording, encodeWAV } from "@/lib/audio";

interface Props {
  onRecording: (blob: Blob) => void;
  onReset?: () => void;
}

const PHRASES = [
  "The quick brown fox jumps over the lazy dog",
  "Every person deserves to have their identity protected",
  "Security and trust go hand in hand always",
  "My voice is my password verify me today",
  "Technology helps us build a safer digital world",
  "A strong password is the first line of defense",
  "Digital identity must be verified not assumed",
  "Protecting data requires constant vigilance and care",
];

function pickRandom(exclude?: number): number {
  let idx: number;
  do {
    idx = Math.floor(Math.random() * PHRASES.length);
  } while (idx === exclude && PHRASES.length > 1);
  return idx;
}

// The Web Speech API is not in TypeScript's built-in types, so we describe
// only the small part we use.
type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  start(): void;
  stop(): void;
};
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

// Check for Web Speech API (Chrome/Edge)
function getSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export default function AudioRecorder({ onRecording, onReset }: Props) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const transcriptRef = useRef<string>("");
  const speechAvailableRef = useRef(false);

  const [phraseIndex, setPhraseIndex] = useState(() => pickRandom());
  const [recording, setRecording] = useState(false);
  const [recorded, setRecorded] = useState(false);
  const [timer, setTimer] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const audioUrlRef = useRef<string | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);

  const phrase = PHRASES[phraseIndex];

  const startRecording = useCallback(async () => {
    setError(null);
    setWarning(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      chunksRef.current = [];

      processor.onaudioprocess = (e) => {
        const channelData = e.inputBuffer.getChannelData(0);
        chunksRef.current.push(new Float32Array(channelData));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      // Start speech recognition if available (Chrome/Edge)
      const SpeechRecognitionAPI = getSpeechRecognition();
      if (SpeechRecognitionAPI) {
        try {
          const recognition = new SpeechRecognitionAPI();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = "en-US";
          transcriptRef.current = "";

          recognition.onresult = (event) => {
            let text = "";
            for (let i = 0; i < event.results.length; i++) {
              text += event.results[i][0].transcript;
            }
            transcriptRef.current = text;
          };

          recognition.onerror = () => {
            // Speech recognition error — will fall back to volume-only checks
            speechAvailableRef.current = false;
          };

          recognition.start();
          recognitionRef.current = recognition;
          speechAvailableRef.current = true;
        } catch {
          speechAvailableRef.current = false;
        }
      } else {
        speechAvailableRef.current = false;
      }

      setRecording(true);
      setTimer(0);
      timerRef.current = setInterval(() => setTimer((t) => t + 1), 1000);
    } catch {
      setError(
        "Could not access microphone. Please allow microphone access in your browser settings."
      );
    }
  }, []);

  const stopRecording = useCallback(() => {
    // FIRST: stop the timer immediately so UI stops counting
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = undefined;
    }
    setRecording(false);

    // Disconnect audio nodes
    sourceRef.current?.disconnect();
    processorRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((t) => t.stop());

    const sampleRate = audioContextRef.current?.sampleRate || 16000;
    audioContextRef.current?.close();
    audioContextRef.current = null;
    sourceRef.current = null;
    processorRef.current = null;
    streamRef.current = null;

    // Stop speech recognition
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
      recognitionRef.current = null;
    }

    // Check length, loudness, distortion and (if available) the spoken words
    const transcript = speechAvailableRef.current ? transcriptRef.current : null;
    const result = checkRecording(chunksRef.current, sampleRate, transcript, phrase);
    if ("error" in result) {
      setError(result.error);
      return;
    }
    if (result.warning) setWarning(result.warning);

    const wavBlob = encodeWAV(chunksRef.current, sampleRate);
    // Create playback URL
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    audioUrlRef.current = URL.createObjectURL(wavBlob);
    onRecording(wavBlob);
    setRecorded(true);
  }, [onRecording, phrase]);

  const playRecording = () => {
    if (!audioUrlRef.current) return;
    if (audioElRef.current) {
      audioElRef.current.pause();
      audioElRef.current = null;
    }
    const audio = new Audio(audioUrlRef.current);
    audioElRef.current = audio;
    setPlaying(true);
    audio.onended = () => setPlaying(false);
    audio.play();
  };

  const stopPlayback = () => {
    if (audioElRef.current) {
      audioElRef.current.pause();
      audioElRef.current.currentTime = 0;
      audioElRef.current = null;
    }
    setPlaying(false);
  };

  const reset = () => {
    stopPlayback();
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setRecorded(false);
    setTimer(0);
    setError(null);
    setWarning(null);
    // Pick a NEW random phrase each time
    setPhraseIndex((prev) => pickRandom(prev));
    onReset?.();
  };

  const speechSupported = typeof window !== "undefined" && getSpeechRecognition() !== null;

  return (
    <div className="space-y-5">
      <blockquote className="border-l-[3px] border-seal bg-seal-tint/50 px-5 py-4 rounded-r-[4px]">
        <p className="text-xl leading-snug text-ink font-medium">{phrase}</p>
        {speechSupported && (
          <p className="mt-2 text-sm text-ink-faint">Your words are compared with this sentence.</p>
        )}
      </blockquote>

      <div aria-live="polite" className="space-y-3 empty:hidden">
        {error && <p className="note note-fail"><span>{error}</span></p>}
        {warning && !error && <p className="note note-review"><span>{warning}</span></p>}
      </div>

      {recorded ? (
        <div className="flex flex-wrap items-center gap-3">
          <p className="note note-pass flex-1 min-w-[14rem]">
            <span>Recording saved ({timer} seconds).</span>
          </p>
          <button onClick={playing ? stopPlayback : playRecording} className="btn btn-quiet">
            {playing ? "Stop playback" : "Play it back"}
          </button>
          <button onClick={reset} className="btn btn-quiet">Record again</button>
        </div>
      ) : recording ? (
        <div className="flex flex-wrap items-center gap-4">
          <button onClick={stopRecording} disabled={timer < MIN_RECORDING_SECONDS} className="btn">
            Stop recording
          </button>
          <p className="flex items-center gap-2 text-ink figures">
            <span className="w-2.5 h-2.5 rounded-full bg-fail motion-safe:animate-pulse" aria-hidden="true" />
            Recording: {timer} s
            {timer < MIN_RECORDING_SECONDS && (
              <span className="text-ink-faint"> — keep going, at least {MIN_RECORDING_SECONDS} seconds</span>
            )}
          </p>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-4">
          <button onClick={startRecording} className="btn">Start recording</button>
          <p className="text-sm text-ink-faint">Read the whole sentence. At least {MIN_RECORDING_SECONDS} seconds.</p>
        </div>
      )}
    </div>
  );
}
