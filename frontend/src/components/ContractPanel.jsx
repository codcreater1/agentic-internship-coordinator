import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Download, FileText, Gavel, Mail, PenLine, Send } from "lucide-react";

import {
  approveApplication,
  contractPreviewUrl,
  sendContract,
  signApplication,
  signedDownloadUrl,
} from "../services/api";

function defaultSubject(app) {
  return `Internship Agreement - ${app.recommended_role}`;
}

function defaultBody(app) {
  const first = (app.name || "").split(" ")[0] || "there";
  return (
    `Dear ${first},\n\n` +
    "Please find attached your internship agreement, signed by the internship " +
    "coordinator.\n\n" +
    "Kindly review the document and keep a copy for your records.\n\n" +
    "Best regards,\n" +
    "Internship Coordination Team"
  );
}

export default function ContractPanel({ selected, refresh }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const inked = useRef(false);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState("");

  // Compose state for the "send by email" step.
  const [composeOpen, setComposeOpen] = useState(false);
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");

  // Coordinator override: manually approve a borderline candidate.
  const [approving, setApproving] = useState(false);
  const [approveError, setApproveError] = useState("");

  // Reset the pad and the compose form whenever a different candidate is selected.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 2.5;
      ctx.lineCap = "round";
      ctx.strokeStyle = "#13111a";
      inked.current = false;
    }
    setError("");
    setComposeOpen(false);
    setSendError("");
    setApproveError("");
    if (selected) {
      setTo(selected.email || "");
      setSubject(defaultSubject(selected));
      setBody(defaultBody(selected));
    }
  }, [selected?.id]);

  if (!selected) {
    return (
      <div className="panel contract">
        <div className="panelHead">
          <div>
            <h3>Contract</h3>
            <p>Agreement &amp; signature</p>
          </div>
        </div>
        <div className="empty">Select a candidate to manage their contract.</div>
      </div>
    );
  }

  const hasContract = Boolean(selected.contract_task_id && selected.contract_pdf_path);
  const signedUrl = signedDownloadUrl(selected.signed_contract_download_url);

  function point(e) {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return {
      x: (t.clientX - rect.left) * (canvas.width / rect.width),
      y: (t.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  function startStroke(e) {
    drawing.current = true;
    const { x, y } = point(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  function moveStroke(e) {
    if (!drawing.current) return;
    e.preventDefault();
    const { x, y } = point(e);
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineTo(x, y);
    ctx.stroke();
    inked.current = true;
  }

  function endStroke() {
    drawing.current = false;
  }

  function clearPad() {
    const canvas = canvasRef.current;
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    inked.current = false;
    setError("");
  }

  async function handleSign() {
    if (!inked.current) {
      setError("Please draw a signature first.");
      return;
    }
    setError("");
    setSigning(true);
    try {
      const dataUrl = canvasRef.current.toDataURL("image/png");
      const updated = await signApplication(selected.id, dataUrl);
      await refresh();
      const url = signedDownloadUrl(updated?.signed_contract_download_url);
      if (url) window.open(url, "_blank");
    } catch {
      setError("Signing failed. Is the backend running?");
    } finally {
      setSigning(false);
    }
  }

  async function handleSend() {
    setSendError("");
    setSending(true);
    try {
      await sendContract(selected.id, { to, subject, body });
      await refresh();
      setComposeOpen(false);
    } catch (err) {
      setSendError(err.message || "Sending failed.");
    } finally {
      setSending(false);
    }
  }

  async function handleApprove() {
    setApproveError("");
    setApproving(true);
    try {
      await approveApplication(selected.id);
      await refresh();
    } catch (err) {
      setApproveError(err.message || "Could not approve this application.");
    } finally {
      setApproving(false);
    }
  }

  return (
    <div className="panel contract">
      <div className="panelHead">
        <div>
          <h3>Contract</h3>
          <p>Internship agreement</p>
        </div>
      </div>

      {!hasContract && (
        <div className="empty">
          <FileText size={36} />
          <p>No contract generated.</p>
          <small>
            {selected?.missing_fields?.length > 0
              ? "The application is missing mandatory placement details — the candidate has been asked for them."
              : selected?.status === "interview"
                ? "Only candidates invited to interview receive an agreement."
                : "The AI did not recommend interview. You can still approve this candidate manually."}
          </small>

          {/* Coordinator override: available when the AI stopped short of
              interview but the mandatory placement details are present. */}
          {selected?.status !== "interview" &&
            !(selected?.missing_fields?.length > 0) && (
              <div className="approveArea">
                <button
                  className="primary"
                  type="button"
                  onClick={handleApprove}
                  disabled={approving}
                >
                  <Gavel size={16} />{" "}
                  {approving ? "Approving…" : "Approve & generate contract"}
                </button>
                {approveError && <p className="signError">{approveError}</p>}
              </div>
            )}
        </div>
      )}

      {hasContract && (
        <>
          <iframe
            className="pdfFrame"
            title="Contract preview"
            src={contractPreviewUrl(selected.id)}
          />

          <a
            className="ghost block"
            href={contractPreviewUrl(selected.id)}
            target="_blank"
            rel="noreferrer"
          >
            <FileText size={15} /> Open PDF in new tab
          </a>

          {signedUrl ? (
            <>
              <div className="signedBox">
                <CheckCircle2 size={18} />
                <div>
                  <strong>Signed by coordinator</strong>
                  <a href={signedUrl} target="_blank" rel="noreferrer">
                    <Download size={14} /> Download signed contract
                  </a>
                </div>
              </div>

              {selected.contract_sent_to ? (
                <div className="sentBox">
                  <Mail size={16} />
                  <div>
                    <strong>Sent to {selected.contract_sent_to}</strong>
                    <small>
                      {new Date(selected.contract_sent_at).toLocaleString()}
                    </small>
                  </div>
                </div>
              ) : !composeOpen ? (
                <div className="sendPrompt">
                  <p>Send this signed agreement to the candidate by email?</p>
                  <button
                    className="primary"
                    type="button"
                    onClick={() => setComposeOpen(true)}
                  >
                    <Mail size={16} /> Yes, compose email
                  </button>
                </div>
              ) : (
                <div className="composeBox">
                  <label className="composeField">
                    <span>To</span>
                    <input
                      type="email"
                      value={to}
                      onChange={(e) => setTo(e.target.value)}
                      placeholder="candidate@example.com"
                    />
                  </label>

                  <label className="composeField">
                    <span>Subject</span>
                    <input
                      type="text"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                    />
                  </label>

                  <label className="composeField">
                    <span>Message</span>
                    <textarea
                      rows={7}
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                    />
                  </label>

                  <p className="composeHint">
                    <FileText size={13} /> The signed PDF is attached automatically.
                  </p>

                  {sendError && <p className="signError">{sendError}</p>}

                  <div className="signButtons">
                    <button
                      className="ghost"
                      type="button"
                      onClick={() => setComposeOpen(false)}
                      disabled={sending}
                    >
                      Cancel
                    </button>
                    <button
                      className="primary"
                      type="button"
                      onClick={handleSend}
                      disabled={sending || !to.trim() || !subject.trim() || !body.trim()}
                    >
                      <Send size={15} /> {sending ? "Sending..." : "Send email"}
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="signArea">
              <p className="signLabel">
                <PenLine size={15} /> Draw coordinator signature
              </p>
              <canvas
                ref={canvasRef}
                width={480}
                height={200}
                className="sigPad"
                onMouseDown={startStroke}
                onMouseMove={moveStroke}
                onMouseUp={endStroke}
                onMouseLeave={endStroke}
                onTouchStart={startStroke}
                onTouchMove={moveStroke}
                onTouchEnd={endStroke}
              />
              {error && <p className="signError">{error}</p>}
              <div className="signButtons">
                <button className="ghost" type="button" onClick={clearPad}>
                  Clear
                </button>
                <button className="primary" type="button" onClick={handleSign} disabled={signing}>
                  <CheckCircle2 size={16} /> {signing ? "Signing..." : "Sign Contract"}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
