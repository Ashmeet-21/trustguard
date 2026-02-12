"""
Risk Scoring Engine — The "brain" that combines all agent results into one decision.

Takes scores from up to 4 detection agents (deepfake, liveness, voice, behavior)
and produces a single trust_score (0-100) with a PASS/REVIEW/FAIL decision.

Weighted scoring:
- Image agent (deepfake): 30% weight
- Video agent (liveness): 25% weight
- Voice agent: 25% weight
- Behavior agent: 20% weight

Decision rules:
- FAIL: trust_score < 40 OR any agent CRITICAL OR 2+ agents flagged
- REVIEW: trust_score 40-69 OR 1 agent flagged HIGH
- PASS: trust_score >= 70 AND no CRITICAL/HIGH agents

INTERVIEW TIP: "The risk engine uses weighted scoring like a school grade.
Each agent is a subject — deepfake detection counts for 30%, liveness 25%, etc.
Then simple decision rules determine the final verdict."
"""

from loguru import logger


class RiskEngine:
    """Aggregates all agent scores into a single trust score and decision."""

    WEIGHTS = {
        "image_agent": 0.30,
        "video_agent": 0.25,
        "voice_agent": 0.25,
        "behavior_agent": 0.20,
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
        if not signals:
            return {
                "trust_score": 0,
                "decision": "FAIL",
                "explanation": ["No detection signals provided"],
                "agents": {},
                "overall_risk": "CRITICAL",
            }

        # Adjust weights for available signals only
        available = {k: v for k, v in self.WEIGHTS.items() if k in signals}
        if not available:
            return {
                "trust_score": 0,
                "decision": "FAIL",
                "explanation": ["No recognized agent signals"],
                "agents": {},
                "overall_risk": "CRITICAL",
            }

        total_weight = sum(available.values())
        normalized_weights = {k: v / total_weight for k, v in available.items()}

        # Calculate weighted trust score (0-100)
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
