import { API_URL } from "./api";

// End-of-internship report packages. Kept beside the application API rather
// than merged into it: the two share a base URL and nothing else. An
// application is a candidate we might take on; a submission is the paperwork
// proving one of them finished.

// The queue endpoint returns compact rows (ReportListItem). Opening one fetches
// the full record — findings, documents, advisory reading — because that
// payload is far too heavy to send for every row in the list.
export async function getReportSubmissions(status) {
  const url = status
    ? `${API_URL}/reports/?status=${encodeURIComponent(status)}`
    : `${API_URL}/reports/`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load completion submissions");
  return res.json();
}

export async function getReportSubmission(submissionId) {
  const res = await fetch(`${API_URL}/reports/by-id/${submissionId}`);
  if (!res.ok) throw new Error("Failed to load this submission");
  return res.json();
}

// Every completion attempt for one candidate, newest first. A student asked to
// correct something and resend produces a second row rather than overwriting
// the first, so this is a history, not a lookup.
export async function getReportsForApplication(applicationId) {
  const res = await fetch(`${API_URL}/reports/for-application/${applicationId}`);
  if (!res.ok) throw new Error("Failed to load completion history");
  return res.json();
}

// The signature gate. The backend refuses to sign a rejected submission or one
// still waiting on the student, and requires acknowledge_warnings for a package
// with open points — so the errors surfaced here are decisions, not faults, and
// the detail text is written to be shown to the coordinator verbatim.
export async function signCertificate(
  submissionId,
  { coordinatorName, signatureImageBase64, acknowledgeWarnings = false, note = "" },
) {
  const res = await fetch(`${API_URL}/reports/by-id/${submissionId}/sign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      coordinator_name: coordinatorName,
      signature_image_base64: signatureImageBase64 || null,
      acknowledge_warnings: acknowledgeWarnings,
      note: note || null,
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || "Signing failed.");
  }
  return res.json();
}

export function reportAttachmentUrl(submissionId, role) {
  return `${API_URL}/reports/by-id/${submissionId}/attachments/${role}`;
}

export function certificateUrl(path) {
  return path ? `${API_URL}${path}` : null;
}
