export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function getApplications() {
  const res = await fetch(`${API_URL}/applications/`);
  if (!res.ok) throw new Error("Failed to load applications");
  return res.json();
}

export async function signApplication(index, signatureImageBase64) {
  const res = await fetch(`${API_URL}/applications/${index}/sign`, {
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

export function contractPreviewUrl(index) {
  return `${API_URL}/applications/${index}/contract-preview`;
}

export function signedDownloadUrl(path) {
  return path ? `${API_URL}${path}` : null;
}