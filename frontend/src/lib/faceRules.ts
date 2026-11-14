// Photo rules for the /verify photo step (pure functions, no React).
// Each returns a message to show the user, or null when the photo is fine.
import type { FaceCheckResult } from "./api";

// Head-turn limits: keep equal to FRONT_MAX_YAW / TURN_MIN_YAW in backend/core/session_orchestrator.py
const FRONT_MAX_YAW = 0.15;
const TURN_MIN_YAW = 0.10;

const EDGE = 0.04; // a face box this close to the image edge counts as cut off

/** Front selfie: a face, not cut off, big enough, and clear enough. */
export function frontPhotoProblem(check: FaceCheckResult): string | null {
  if (!check.faceDetected) {
    return "No face found. Take a clear selfie with your whole face inside the oval.";
  }
  const bbox = check.faceBbox;
  if (!bbox) return null; // server gave no box: let the full verification decide

  const cutSides: string[] = [];
  if (bbox.x_min < EDGE) cutSides.push("left");
  if (bbox.y_min < EDGE) cutSides.push("top");
  if (bbox.x_max > 1 - EDGE) cutSides.push("right");
  if (bbox.y_max > 1 - EDGE) cutSides.push("bottom");
  if (cutSides.length > 0) {
    return `Your face is cut off at the ${cutSides.join(" and ")}. Centre your whole face inside the oval.`;
  }
  if (bbox.width_pct < 0.15 || bbox.height_pct < 0.18) {
    return "Your face is too small in the photo. Move closer so it fills the oval.";
  }
  if (check.livenessScore < 0.3) {
    return "The photo looks blurry or taken from a screen. Take a sharp, well-lit selfie directly with your camera.";
  }
  if (check.livenessScore < 0.5) {
    return "The photo is unclear. Find better light and hold the camera steady.";
  }
  return null;
}

/**
 * Head-turn photo: same rule as the server (session_orchestrator.py), so people
 * can retake BEFORE the one-shot verification. challenge is null if no session yet.
 */
export function headTurnProblem(
  check: FaceCheckResult,
  frontYaw: number | null,
  challenge: "left" | "right" | null
): string | null {
  if (!challenge || !check.faceDetected || check.headYaw === null) {
    return "No face found in the second photo. Keep your face in view and try again.";
  }
  if (frontYaw === null || Math.abs(frontYaw) > FRONT_MAX_YAW) {
    return "Your first photo was not straight. Take a different first photo, looking at the camera.";
  }
  const change = check.headYaw - frontYaw;
  const turnedEnough = challenge === "left" ? change <= -TURN_MIN_YAW : change >= TURN_MIN_YAW;
  return turnedEnough ? null : `Turn a bit more towards your ${challenge} shoulder, then take the photo again.`;
}
