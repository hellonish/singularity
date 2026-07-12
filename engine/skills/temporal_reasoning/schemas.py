from pydantic import BaseModel, ConfigDict


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    timezone_name: str = "UTC"


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    iso_time: str
    timezone_name: str
    explanation: str
