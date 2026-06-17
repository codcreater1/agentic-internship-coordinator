from app.agents.workflow import graph


class ApplicationService:

    @staticmethod
    def evaluate(cv_text: str):
        result = graph.invoke({"cv_text": cv_text})

        score = result.get("candidate_score", 85)

        if score >= 80:
            status = "interview"
            email_subject = "Internship Application - Interview Invitation"
            email_body = (
                "Dear Candidate,\n\n"
                "Thank you for your internship application. "
                "After reviewing your profile, we would like to invite you "
                "to the next stage of the process.\n\n"
                "Best regards,\n"
                "Internship Coordination Team"
            )
        elif score >= 60:
            status = "pending"
            email_subject = "Internship Application - Under Review"
            email_body = (
                "Dear Candidate,\n\n"
                "Thank you for your internship application. "
                "Your profile is currently under review. "
                "We may contact you for additional information.\n\n"
                "Best regards,\n"
                "Internship Coordination Team"
            )
        else:
            status = "rejected"
            email_subject = "Internship Application Result"
            email_body = (
                "Dear Candidate,\n\n"
                "Thank you for your interest in our internship program. "
                "After reviewing your application, we will not proceed "
                "with your application at this time.\n\n"
                "Best regards,\n"
                "Internship Coordination Team"
            )

        return {
            "candidate_score": score,
            "recommended_role": result.get(
                "recommendation",
                "Backend Developer Internship",
            ),
            "status": status,
            "report": result.get("report", "No report generated."),
            "email_subject": email_subject,
            "email_body": email_body,
        }
