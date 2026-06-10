from app.agents.workflow import graph


class ApplicationService:

    @staticmethod
    def evaluate(cv_text: str):
        result = graph.invoke({"cv_text": cv_text})

        score = result.get("candidate_score", 85)

        if score >= 80:
            status = "interview"
        elif score >= 60:
            status = "pending"
        else:
            status = "rejected"

        return {
            "candidate_score": score,
            "recommended_role": result.get(
                "recommendation",
                "Backend Developer Internship",
            ),
            "status": status,
            "report": result.get("report", "No report generated."),
        }