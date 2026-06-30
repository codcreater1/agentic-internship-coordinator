from pydantic import BaseModel, EmailStr


class Application(BaseModel):
    name: str
    email: EmailStr
    cv_text: str


class SignApplicationRequest(BaseModel):
    signature_image_base64: str
    x: float = 70
    y: float = 600
    w: float = 220
    h: float = 70


class ApplicationResponse(BaseModel):
    name: str
    email: EmailStr
    candidate_score: int
    recommended_role: str
    status: str
    report: str
    email_subject: str
    email_body: str
    contract_pdf_path: str | None = None
    signed_contract_path: str | None = None
    contract_task_id: str | None = None
    signed_contract_download_url: str | None = None