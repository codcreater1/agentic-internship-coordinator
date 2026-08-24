import { useEffect, useRef, useState } from "react";
import {
  Award,
  CheckCircle2,
  Download,
  Lock,
  PenLine,
  ShieldAlert,
} from "lucide-react";

import { certificateUrl, signCertificate } from "../services/reportsApi";

// Remembered across submissions: a coordinator signing a queue should not
// retype their own name for every student. Stored locally only — the backend
// records it per signature.
const NAME_KEY = "aic.coordinatorName";

export default function CertificatePanel({ selected, refresh }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const inked = useRef(false);

  const [coordinatorName, setCoordinatorName] = useState(
    () => localStorage.getItem(NAME_KEY) || "",
  );
  const [acknowledged, setAcknowledged] = useState(false);
  const [note, setNote] = useState("");
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState("");

  // Reset the pad and the per-submission fields whenever the selection changes.
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
    setAcknowledged(false);
    setNote("");
    setError("");
  }, [selected?.id]);

  if (!selected) {
    return (
      <div className="panel contract">
        <div className="panelHead">
          <div>
            <h3>Certificate</h3>
            <p>Completion &amp; signature</p>
          </div>
        </div>
        <div className="empty">Select a submission to issue its certificate.</div>
      </div>
    );
  }

  const signedUrl = certificateUrl(selected.signed_certificate_download_url);
  const warnings = (selected.findings || []).filter((f) => f.severity === "warning");
  const blocked =
    selected.status === "rejected" || selected.status === "request_clarification";
  const needsAcknowledgement = selected.status === "pending";

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
    if (!coordinatorName.trim()) {
      setError("Enter your name — it is printed on the certificate.");
      return;
    }
    if (!inked.current) {
      setError("Please draw a signature first.");
      return;
    }

    setError("");
    setSigning(true);
    try {
      localStorage.setItem(NAME_KEY, coordinatorName.trim());
      const updated = await signCertificate(selected.id, {
        coordinatorName: coordinatorName.trim(),
        signatureImageBase64: canvasRef.current.toDataURL("image/png"),
        acknowledgeWarnings: acknowledged,
        note,
      });
      await refresh();
      const url = certificateUrl(updated?.signed_certificate_download_url);
      if (url) window.open(url, "_blank");
    } catch (err) {
      // The backend's refusals are written for a person to read.
      setError(err.message || "Signing failed.");
    } finally {
      setSigning(false);
    }
  }

  return (
    <div className="panel contract">
      <div className="panelHead">
        <div>
          <h3>Certificate</h3>
          <p>Internship completion</p>
        </div>
      </div>

      {signedUrl ? (
        <>
          <div className="signedBox">
            <Award size={18} />
            <div>
              <strong>Signed by {selected.signed_by}</strong>
              <a href={signedUrl} target="_blank" rel="noreferrer">
                <Download size={14} /> Download certificate
              </a>
            </div>
          </div>
          {selected.coordinator_note && (
            <p className="findingNote">Note: {selected.coordinator_note}</p>
          )}
          <p className="findingNote">
            The certificate carries the hash of the three submitted documents.
            Rehash them to check it later.
          </p>
        </>
      ) : blocked ? (
        <div className="empty">
          <Lock size={36} />
          <p>Cannot be signed yet.</p>
          <small>
            {selected.status === "rejected"
              ? "This submission cannot be approved automatically. Contact the student directly — signing is not available."
              : "The student has been asked to correct and resend. Signing now would certify an incomplete record."}
          </small>
        </div>
      ) : (
        <div className="signArea">
          <label className="composeField">
            <span>Your name</span>
            <input
              type="text"
              value={coordinatorName}
              onChange={(e) => setCoordinatorName(e.target.value)}
              placeholder="e.g. dr Anna Zielińska"
            />
          </label>

          {needsAcknowledgement && (
            <div className="ackBox">
              <ShieldAlert size={16} />
              <div>
                <strong>
                  {warnings.length} open point
                  {warnings.length === 1 ? "" : "s"} on this submission
                </strong>
                <p>
                  Signing anyway records them on the certificate. Read them in
                  the panel to the left first.
                </p>
                <label className="ackCheck">
                  <input
                    type="checkbox"
                    checked={acknowledged}
                    onChange={(e) => setAcknowledged(e.target.checked)}
                  />
                  <span>I have reviewed these and accept them.</span>
                </label>
              </div>
            </div>
          )}

          <label className="composeField">
            <span>Note (optional)</span>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Recorded with the decision"
            />
          </label>

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
            <button
              className="primary"
              type="button"
              onClick={handleSign}
              disabled={signing || (needsAcknowledgement && !acknowledged)}
            >
              <CheckCircle2 size={16} />{" "}
              {signing ? "Signing..." : "Sign certificate"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
