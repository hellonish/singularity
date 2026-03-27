"""claim_verification — verifies synthesis claims against cited sources."""
from ..base import BaseAnalysisSkill


class ClaimVerificationSkill(BaseAnalysisSkill):
    name = "claim_verification"
    PROMPT_FILE = "claim_verification.md"
