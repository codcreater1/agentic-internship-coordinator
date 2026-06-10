from pydantic import BaseModel, EmailStr


class Application(BaseModel):
    name: str
    email: EmailStr
    cv_text: str


class ApplicationResponse(BaseModel):
    name: str
    email: EmailStr
    candidate_score: int
    recommended_role: str
    status: str
    report: str