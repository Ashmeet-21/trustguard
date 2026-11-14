// Pure audio helpers for AudioRecorder (no React, no browser APIs).

export const MIN_RECORDING_SECONDS = 3;
const SILENCE_THRESHOLD = 0.01;
const MIN_WORD_MATCH = 40; // At least 40% of words must match

/**
 * Encode raw PCM float samples into a WAV file blob.
 */
export function encodeWAV(samples: Float32Array[], sampleRate: number): Blob {
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

/** Compare spoken transcript words against target phrase words (0-100) */
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

/**
 * Check a finished recording. Returns an error (recording rejected) or an
 * optional warning (recording accepted).
 * transcript is null when speech recognition was not available.
 */
export function checkRecording(
  chunks: Float32Array[],
  sampleRate: number,
  transcript: string | null,
  phrase: string
): { error: string } | { warning: string | null } {
  // 1. Long enough?
  const totalSamples = chunks.reduce((acc, c) => acc + c.length, 0);
  const seconds = Math.floor(totalSamples / sampleRate);
  if (seconds < MIN_RECORDING_SECONDS) {
    return {
      error: `Recording too short (${seconds}s). Please record at least ${MIN_RECORDING_SECONDS} seconds of speech.`,
    };
  }

  // 2. Not silent?
  const rms = calculateRMS(chunks);
  if (rms < SILENCE_THRESHOLD) {
    return {
      error: "No speech detected — the recording was silent. Please speak clearly into your microphone and try again.",
    };
  }

  // 3. Not crackling? (over 5% clipped samples)
  const clipRatio = detectClipping(chunks);
  if (clipRatio > 0.05) {
    return {
      error: "Audio is crackling or distorted — your microphone input is too loud. Please move further from the mic or lower your input volume, then try again.",
    };
  }

  // 4. Said the right words? (only if the browser gave us a transcript)
  let matchWarning: string | null = null;
  if (transcript !== null) {
    const spoken = transcript.trim();
    if (spoken.length === 0) {
      return {
        error: "Could not recognize any speech. Please speak clearly and read the exact phrase displayed above.",
      };
    }
    const match = wordMatch(spoken, phrase);
    if (match < MIN_WORD_MATCH) {
      return {
        error: `Speech didn't match the phrase (${match}% match, need ${MIN_WORD_MATCH}%). Please read the exact phrase shown above.`,
      };
    }
    if (match < 70) {
      matchWarning = `Partial match detected (${match}%). Recording accepted, but reading the exact phrase improves accuracy.`;
    }
  }

  // Accepted. Audio-quality warnings take priority over the match warning.
  if (clipRatio > 0.02) {
    return { warning: "Slight audio distortion detected. Recording accepted, but speaking at a normal volume gives better results." };
  }
  if (rms < SILENCE_THRESHOLD * 3) {
    return { warning: "Low audio level detected. The recording was accepted but speaking louder may improve results." };
  }
  return { warning: matchWarning };
}
