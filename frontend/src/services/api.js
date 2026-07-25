export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function getApplications() {
  const res = await fetch(`${API_URL}/applications/`);
  if (!res.ok) throw new Error("Failed to load applications");
  return res.json();
}

// Candidates are addressed by their stable id, never by list position: new
// applications arrive from n8n continuously and the list is newest-first, so
// an index captured at page load can point at a different candidate by the
// time the coordinator signs.
export async function signApplication(applicationId, signatureImageBase64) {
  const res = await fetch(`${API_URL}/applications/by-id/${applicationId}/sign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      signature_image_base64: signatureImageBase64,
      x: 70,
      y: 600,
      w: 220,
      h: 70,
    }),
  });

  if (!res.ok) throw new Error("Signing failed");
  return res.json();
}

export async function sendContract(applicationId, { to, subject, body }) {
  const res = await fetch(`${API_URL}/applications/by-id/${applicationId}/send-contract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to, subject, body }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || "Sending failed");
  }
  return res.json();
}

export async function approveApplication(applicationId) {
  const res = await fetch(`${API_URL}/applications/by-id/${applicationId}/approve`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || "Could not approve this application.");
  }
  return res.json();
}

export function contractPreviewUrl(applicationId) {
  return `${API_URL}/applications/by-id/${applicationId}/contract-preview`;
}

export function signedDownloadUrl(path) {
  return path ? `${API_URL}${path}` : null;
}