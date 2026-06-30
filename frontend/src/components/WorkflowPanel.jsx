import { Brain, CheckCircle2, Clock3, FileText, Mail, PenLine } from "lucide-react";
import { signedDownloadUrl } from "../services/api";

export default function WorkflowPanel({ selected }) {
  const downloadUrl = signedDownloadUrl(selected?.signed_contract_download_url);

  return (
    <div className="panel workflow">
      <div className="panelHead">
        <div>
          <h3>Workflow</h3>
          <p>Automation status</p>
        </div>
      </div>

      <div className="timeline">
        <div className="step done">
          <CheckCircle2 size={18} />
          <div>
            <strong>Email received</strong>
            <p>Candidate mail captured by n8n</p>
          </div>
        </div>

        <div className="step done">
          <Brain size={18} />
          <div>
            <strong>AI analysis</strong>
            <p>CV evaluated by FastAPI workflow</p>
          </div>
        </div>

        <div className={selected?.contract_task_id ? "step done" : "step"}>
          <FileText size={18} />
          <div>
            <strong>Contract generated</strong>
            <p>Internship agreement created</p>
          </div>
        </div>

        <div className={downloadUrl ? "step done" : "step"}>
          <PenLine size={18} />
          <div>
            <strong>Coordinator signature</strong>
            <p>{downloadUrl ? "Contract signed" : "Waiting for manual signature"}</p>
          </div>
        </div>

        <div className="step">
          <Mail size={18} />
          <div>
            <strong>Email delivery</strong>
            <p>Ready for n8n Gmail node</p>
          </div>
        </div>

        <div className="step">
          <Clock3 size={18} />
          <div>
            <strong>Audit log</strong>
            <p>Waiting for final delivery event</p>
          </div>
        </div>
      </div>
    </div>
  );
}