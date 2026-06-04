from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import logging

# =========================
# LOGGING (TRACK + TRAIL)
# =========================
logging.basicConfig(filename="audit.log", level=logging.INFO)


def audit_log(actor, action, data_id):
    logging.info(f"{actor} | {action} | {data_id}")


# =========================
# DATA MODEL
# =========================
class LoanApplication(BaseModel):
    applicant_id: str
    income: float
    requested_amount: float
    documents_verified: bool
    device_id: str


class RiskReport(BaseModel):
    applicant_id: str
    risk_score: float
    flags: List[str]
    confidence: float
    recommended_action: str


# =========================
# KILL SWITCH
# =========================
class KillSwitch:
    active = False

    def trigger(self, reason: str):
        self.active = True
        audit_log("SYSTEM", "KILL_SWITCH_TRIGGERED", reason)
        print(f"🛑 SYSTEM HALTED: {reason}")

    def check(self):
        if self.active:
            raise Exception("System is frozen by kill switch")


# =========================
# IRP AGENT (RISK FILTER)
# =========================
class IRPAgent:

    def evaluate(self, app: LoanApplication) -> RiskReport:

        audit_log("IRP", "EVALUATE_APPLICATION", app.applicant_id)

        flags = []
        risk_score = 0.2

        if app.income <= 0:
            flags.append("invalid_income")
            risk_score += 0.4

        if not app.documents_verified:
            flags.append("unverified_documents")
            risk_score += 0.3

        if app.requested_amount > app.income * 5:
            flags.append("high_loan_ratio")
            risk_score += 0.3

        confidence = 0.75 if not flags else 0.55

        return RiskReport(
            applicant_id=app.applicant_id,
            risk_score=min(risk_score, 1.0),
            flags=flags,
            confidence=confidence,
            recommended_action="escalate"
        )


# =========================
# CDC AGENT (DECISION MAKER)
# =========================
class CDCAgent:

    def decide(self, app: LoanApplication, risk: RiskReport):

        audit_log("CDC", "DECISION_START", app.applicant_id)

        if risk.risk_score > 0.7:
            return {"decision": "REJECT", "reason": "High risk score"}

        if risk.risk_score > 0.4:
            return {"decision": "MANUAL_REVIEW", "reason": "Moderate risk"}

        max_loan = app.income * 10
        approved = min(app.requested_amount, max_loan)

        return {
            "decision": "APPROVE",
            "approved_amount": approved,
            "interest_rate": 0.12
        }


# =========================
# PIPELINE (RANK + TRAIL)
# =========================
class RANKPipeline:

    def __init__(self):
        self.irp = IRPAgent()
        self.cdc = CDCAgent()
        self.kill_switch = KillSwitch()

    def process(self, app: LoanApplication):

        self.kill_switch.check()

        # IRP step
        risk = self.irp.evaluate(app)

        audit_log("IRP", "RISK_GENERATED", app.applicant_id)

        # KILL SWITCH CONDITION
        if risk.risk_score > 0.9:
            self.kill_switch.trigger("Extreme fraud risk detected")
            return {"status": "halted"}

        # CDC step (handoff)
        decision = self.cdc.decide(app, risk)

        audit_log("CDC", "DECISION_MADE", app.applicant_id)

        return {
            "risk_report": risk.dict(),
            "decision": decision
        }


# =========================
# FASTAPI SYSTEM ENTRY
# =========================
app = FastAPI()
pipeline = RANKPipeline()


@app.post("/loan")
def process_loan(application: LoanApplication):

    result = pipeline.process(application)

    return {
        "status": "processed",
        "result": result
    }
