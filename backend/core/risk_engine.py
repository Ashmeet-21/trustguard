"""
Risk Scoring Engine - combines all agent results into one decision.

Takes scores from up to 4 detection agents (deepfake, liveness, voice, behavior)
and produces a single trust_score (0-100) with a PASS/REVIEW/FAIL decision.

Weighted scoring (weights are re-scaled so the agents that ran add up to 100%):
- Image agent (deepfake): 40%
- Video agent (liveness): 10%
- Voice agent: 25%
- Behavior agent: 25%

Decision rules ("flagged" = agent risk_level is HIGH or CRITICAL):
- FAIL: trust_score < 40 OR any agent CRITICAL OR 2+ agents flagged
- REVIEW: trust_score < 70 OR 1 agent flagged
- PASS: everything else

INTERVIEW TIP: "The risk engine works like a school grade.
Each agent is a subject with a weight, the weighted average is the score,
and a few simple rules turn the score into PASS / REVIEW / FAIL."
"""

from loguru import logger


class RiskEngine:
    """Aggregates all agent scores into a single trust score and decision."""

    WEIGHTS = {
        "image_agent": 0.40,
        "video_agent": 0.10,  # liveness: weak on full-size photos (AUC 0.80, see benchmarks/LIVENESS_RESULTS.md)
        "voice_agent": 0.25,
        "behavior_agent": 0.25,
    }

    def calculate(self, signals: dict) -> dict:
        """
        Calculate trust score and decision from agent signals.

        Args:
            signals: dict of agent results, e.g.:
                {
                    "image_agent": {"score": 85, "risk_level": "LOW", "details": {...}},
                    "voice_agent": {"score": 30, "risk_level": "HIGH", "details": {...}},
                    ...
                }

        Returns:
            dict with trust_score, decision, explanation, per-agent breakdown
        """
        # Keep only the agents we know about, then re-scale their weights to add up to 1
        available = {k: v for k, v in self.WEIGHTS.items() if k in (signals or {})}
        if not available:
            reason = "No recognized agent signals" if signals else "No detection signals provided"
            return {
                "trust_score": 0,
                "decision": "FAIL",
                "explanation": [reason],
                "agents": {},
                "overall_risk": "CRITICAL",
            }

        total_weight = sum(available.values())
        normalized_weights = {k: v / total_weight for k, v in available.items()}

        # Weighted trust score (0-100). Note: "FLAGGED" in the explanation text uses score < 60,
        # while the decision rules below count risk_level HIGH/CRITICAL.
        trust_score = 0
        explanation = []
        flagged_agents = 0
        has_critical = False

        for agent_name, weight in normalized_weights.items():
            signal = signals[agent_name]
            agent_score = signal.get("score", 0)
            risk_level = signal.get("risk_level", "MEDIUM")

            trust_score += weight * agent_score

            # Build explanation
            status = "PASSED" if agent_score >= 60 else "FLAGGED"
            explanation.append(f"{agent_name}: {status} (score {agent_score}/100, risk {risk_level})")

            # Track flags
            if risk_level == "CRITICAL":
                has_critical = True
                flagged_agents += 1
            elif risk_level == "HIGH":
                flagged_agents += 1

        trust_score = round(trust_score, 1)

        # Decision rules
        if trust_score < 40 or has_critical or flagged_agents >= 2:
            decision = "FAIL"
        elif trust_score < 70 or flagged_agents >= 1:
            decision = "REVIEW"
        else:
            decision = "PASS"

        # Overall risk from trust score
        if trust_score >= 80:
            overall_risk = "LOW"
        elif trust_score >= 60:
            overall_risk = "MEDIUM"
        elif trust_score >= 40:
            overall_risk = "HIGH"
        else:
            overall_risk = "CRITICAL"

        logger.info("Risk engine: trust_score={}, decision={}, agents={}", trust_score, decision, list(signals.keys()))

        return {
            "trust_score": trust_score,
            "decision": decision,
            "explanation": explanation,
            "agents": {k: signals[k] for k in available},
            "overall_risk": overall_risk,
        }
