"""
Quality Gates — Validation rules that run BEFORE the final decision.

Three gates:
1. Replay Protection — have we seen this exact file before? (SHA256 hash check)
2. Minimum Signals — at least 2 agents must have completed
3. Signal Agreement — flags if agents wildly disagree (one says PASS, another CRITICAL)

INTERVIEW TIP: "Quality gates are like a pre-flight checklist. Even if the risk
engine says PASS, we still check: is this a replay attack? Did enough agents run?
Do the agents agree? If any gate fails, we flag it."
"""

import hashlib
from collections import OrderedDict
from loguru import logger


class QualityGateChecker:
    """Enforces validation rules before finalizing a verification decision."""

    def __init__(self, max_hashes: int = 1000):
        # LRU-style hash cache — stores recent file hashes to detect replays
        self._recent_hashes = OrderedDict()
        self._max_hashes = max_hashes

    def run_all_gates(self, session_result: dict, file_hash: str = None) -> list:
        """
        Run all quality gates and return results.

        Returns:
            List of gate results: [{"gate": "replay_protection", "passed": True}, ...]
        """
        gates = []

        if file_hash:
            gates.append({
                "gate": "replay_protection",
                "passed": self.check_replay(file_hash, session_result.get("session_id", "")),
            })

        gates.append({
            "gate": "minimum_signals",
            "passed": self.check_minimum_signals(session_result),
        })

        gates.append({
            "gate": "signal_agreement",
            "passed": self.check_signal_agreement(session_result),
        })

        return gates

    def check_replay(self, file_hash: str, session_id: str) -> bool:
        """
        Check if we've seen this exact file before (replay attack prevention).

        Uses SHA256 hash of the uploaded file. If the same hash was submitted
        recently, it's likely a replay — someone resubmitting the same image.

        Returns True if the file is NEW (not a replay), False if it's a replay.
        """
        if file_hash in self._recent_hashes:
            prev_session = self._recent_hashes[file_hash]
            if prev_session != session_id:
                logger.warning("Replay detected! Hash {} was used in session {}", file_hash[:16], prev_session[:8])
                return False

        # Store this hash
        self._recent_hashes[file_hash] = session_id
        # Evict oldest if cache is full
        if len(self._recent_hashes) > self._max_hashes:
            self._recent_hashes.popitem(last=False)

        return True

    def check_minimum_signals(self, session_result: dict) -> bool:
        """
        At least 2 agents must have completed for a reliable decision.

        A single agent can be fooled, but fooling 2+ is much harder.
        Returns True if >= 2 agents contributed.
        """
        agents = session_result.get("agents", {})
        completed = sum(1 for a in agents.values() if "error" not in a)
        return completed >= 2

    def check_signal_agreement(self, session_result: dict) -> bool:
        """
        Check if agents roughly agree. If one says LOW risk and another
        says CRITICAL, something is suspicious.

        Returns True if agents agree (no extreme disagreement).
        """
        agents = session_result.get("agents", {})
        risk_levels = [a.get("risk_level", "MEDIUM") for a in agents.values() if "error" not in a]

        if len(risk_levels) < 2:
            return True  # Not enough signals to disagree

        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        risk_values = [risk_order.get(r, 1) for r in risk_levels]

        # Flag if the gap between min and max risk is >= 3 (e.g., LOW vs CRITICAL)
        return (max(risk_values) - min(risk_values)) < 3

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
