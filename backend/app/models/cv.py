from pydantic import BaseModel, EmailStr


class CVAnalysisResponse(BaseModel):
    name: str
    email: EmailStr
    filename: str
    extracted_text_preview: str
    candidate_score: int
    recommended_role: str
    status: str
    report: str
    email_subject: str
    email_body: str
    contract_task_id: str | None = None
    signed_contract_download_url: str | None = None