from app.agents.workflow import graph


class ApplicationService:

    @staticmethod
    def evaluate(cv_text: str):
        result = graph.invoke({"cv_text": cv_text})

        text = cv_text.lower()

        positive_keywords = [
            "python", "fastapi", "java", "spring", "c++", "sql",
            "postgresql", "docker", "git", "github", "linux",
            "rest api", "backend", "redis", "api integration",
            "internship", "project", "software", "database"
        ]

        negative_phrases = [
            "no programming",
            "no backend",
            "no docker",
            "no git",
            "no database",
            "no experience",
            "no professional experience",
            "no projects",
            "no internship experience",
            "basic computer knowledge",
            "internet browsing",
            "microsoft word",
            "powerpoint",
            "looking for any job",
        ]

        score = 0

        for keyword in positive_keywords:
            if keyword in text:
                score += 8

        for phrase in negative_phrases:
            if phrase in text:
                score -= 12

        score = max(0, min(score, 100))

        if score >= 70:
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
        elif score >= 50:
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
            "report": f"Candidate score: {score}. Recommended role: "
                      f"{result.get('recommendation', 'Backend Developer Internship')}.",
            "email_subject": email_subject,
            "email_body": email_body,
        }
