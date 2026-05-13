"use client";

import { useRef, useState, useCallback } from "react";

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

const MIN_RECORDING_SECONDS = 3;
const SILENCE_THRESHOLD = 0.01;
const MIN_WORD_MATCH = 40; // At least 40% of words must match

function pickRandom(exclude?: number): number {
  let idx: number;
  do {
    idx = Math.floor(Math.random() * PHRASES.length);
  } while (idx === exclude && PHRASES.length > 1);
  return idx;
}

/**
 * Encode raw PCM float samples into a WAV file blob.
 */
function encodeWAV(samples: Float32Array[], sampleRate: number): Blob {
  const totalLength = samples.reduce((acc, s) => acc + s.length, 0);
  const buffer = new ArrayBuffer(44 + totalLength * 2);
  const view = new DataView(buffer);

  function writeStr(offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + totalLength * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, totalLength * 2, true);

  let offset = 44;
  for (const chunk of samples) {
    for (let i = 0; i < chunk.length; i++) {
      const s = Math.max(-1, Math.min(1, chunk[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
  }

  return new Blob([buffer], { type: "audio/wav" });
}

/** Calculate RMS (loudness) of audio chunks — 0 means silence */
function calculateRMS(chunks: Float32Array[]): number {
  let sumSquares = 0;
  let count = 0;
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++) {
      sumSquares += chunk[i] * chunk[i];
      count++;
    }
  }
  return count > 0 ? Math.sqrt(sumSquares / count) : 0;
}

/**
 * Detect audio clipping/crackling — samples hitting max amplitude.
 * Returns the fraction of samples that are clipped (>= 0.99 amplitude).
 * Above ~2% clipping = crackling/distorted audio.
 */
function detectClipping(chunks: Float32Array[]): number {
  let clipped = 0;
  let total = 0;
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++) {
      total++;
      if (Math.abs(chunk[i]) >= 0.99) clipped++;
    }
  }
  return total > 0 ? clipped / total : 0;
}

/** Compare spoken transcript words against target phrase words */
function wordMatch(spoken: string, target: string): number {
  const spokenWords = spoken.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const targetWords = target.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if (targetWords.length === 0) return 0;
  let matched = 0;
  for (const tw of targetWords) {
    if (spokenWords.some((sw) => sw === tw || sw.includes(tw) || tw.includes(sw))) {
      matched++;
    }
  }
  return Math.round((matched / targetWords.length) * 100);
}

// Check for Web Speech API (Chrome/Edge)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getSpeechRecognition(): any {
  if (typeof window === "undefined") return null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export default function AudioRecorder({ onRecording, onReset }: Props) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
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

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          recognition.onresult = (event: any) => {
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

    // Validate minimum duration
    const currentTimer = chunksRef.current.length > 0
      ? Math.floor((chunksRef.current.reduce((acc, c) => acc + c.length, 0) / sampleRate))
      : 0;

    if (currentTimer < MIN_RECORDING_SECONDS) {
      setError(
        `Recording too short (${currentTimer}s). Please record at least ${MIN_RECORDING_SECONDS} seconds of speech.`
      );
      return;
    }

    // Check for silence
    const rms = calculateRMS(chunksRef.current);
    if (rms < SILENCE_THRESHOLD) {
      setError(
        "No speech detected — the recording was silent. Please speak clearly into your microphone and try again."
      );
      return;
    }

    // Check for clipping/crackling — distorted audio gives bad results
    const clipRatio = detectClipping(chunksRef.current);
    if (clipRatio > 0.05) {
      setError(
        "Audio is crackling or distorted — your microphone input is too loud. Please move further from the mic or lower your input volume, then try again."
      );
      return;
    }

    // Speech content validation (if Web Speech API was available)
    if (speechAvailableRef.current) {
      const transcript = transcriptRef.current.trim();
      if (transcript.length === 0) {
        setError(
          "Could not recognize any speech. Please speak clearly and read the exact phrase displayed above."
        );
        return;
      }

      const match = wordMatch(transcript, phrase);
      if (match < MIN_WORD_MATCH) {
        setError(
          `Speech didn't match the phrase (${match}% match, need ${MIN_WORD_MATCH}%). Please read the exact phrase shown above.`
        );
        return;
      }

      // Low match warning (still accept)
      if (match < 70) {
        setWarning(
          `Partial match detected (${match}%). Recording accepted, but reading the exact phrase improves accuracy.`
        );
      }
    }

    // Crackling warning for borderline (2-5% clipping) — still accept
    let newWarning: string | null = null;
    if (clipRatio > 0.02) {
      newWarning = "Slight audio distortion detected. Recording accepted, but speaking at a normal volume gives better results.";
    }

    // Low volume warning (still accept)
    if (rms < SILENCE_THRESHOLD * 3 && !newWarning) {
      newWarning = "Low audio level detected. The recording was accepted but speaking louder may improve results.";
    }

    if (newWarning) setWarning(newWarning);

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
    <div className="space-y-4">
      <div className="bg-[#0d0520] border border-[#2d1b69] rounded-xl p-4 text-center">
        <p className="text-xs text-[#999] mb-2 uppercase tracking-wider">
          Please read this aloud
        </p>
        <p className="text-lg text-white font-medium">&ldquo;{phrase}&rdquo;</p>
        {speechSupported && (
          <p className="text-xs text-[#555] mt-2">
            Your speech will be checked against the phrase above
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3 text-xs">
          {error}
        </div>
      )}

      {warning && !error && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 rounded-lg p-3 text-xs">
          {warning}
        </div>
      )}

      {recorded ? (
        <div className="bg-[#0d2e1a] border border-[#166534] rounded-xl p-4 text-center">
          <div className="text-2xl mb-2">&#9989;</div>
          <p className="text-[#4ade80] font-medium">
            Voice sample recorded ({timer}s)
          </p>
          <div className="flex items-center justify-center gap-4 mt-3">
            <button
              onClick={playing ? stopPlayback : playRecording}
              className="flex items-center gap-1.5 text-sm text-[#00d4ff] hover:text-white border border-[#00d4ff]/30 px-4 py-1.5 rounded-lg transition"
            >
              {playing ? (
                <>
                  <span>&#9724;</span> Stop
                </>
              ) : (
                <>
                  <span>&#9654;</span> Listen
                </>
              )}
            </button>
            <button
              onClick={reset}
              className="text-xs text-[#666] hover:text-white underline"
            >
              Record again
            </button>
          </div>
        </div>
      ) : recording ? (
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            <span className="text-red-400 text-sm font-medium">
              Recording... {timer}s
            </span>
          </div>
          {timer < MIN_RECORDING_SECONDS && (
            <p className="text-xs text-[#666]">
              Keep speaking... minimum {MIN_RECORDING_SECONDS}s required
            </p>
          )}
          <button
            onClick={stopRecording}
            disabled={timer < MIN_RECORDING_SECONDS}
            className="bg-red-500/20 text-red-400 border border-red-500/30 px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-red-500/30 transition disabled:opacity-30 disabled:cursor-not-allowed"
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
            Start Recording
          </button>
          <p className="text-xs text-[#666] mt-2">
            Record at least {MIN_RECORDING_SECONDS} seconds — read the phrase above clearly
          </p>
        </div>
      )}
    </div>
  );
}
