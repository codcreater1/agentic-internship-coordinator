from pydantic import BaseModel, EmailStr, Field


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
    # Placement details, so a `request_clarification` result explains itself
    # here too and not only on the dashboard's application record.
    company_name: str = ""
    supervisor_name: str = ""
    supervisor_contact: str = ""
    missing_fields: list[str] = Field(default_factory=list)
    contract_task_id: str | None = None
    signed_contract_download_url: str | None = None