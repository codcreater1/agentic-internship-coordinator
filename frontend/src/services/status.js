// Decision vocabulary shared by the dashboard. `request_clarification` means
// the candidate looks good but the application is missing a mandatory
// placement detail, so no agreement exists yet.
export const STATUS_LABELS = {
  interview: "interview",
  pending: "pending",
  rejected: "rejected",
  request_clarification: "needs info",
};

export const MISSING_FIELD_LABELS = {
  company_name: "the host organisation",
  supervisor_name: "the workplace supervisor",
  supervisor_contact: "the supervisor's contact details",
};

export function statusLabel(status = "") {
  return STATUS_LABELS[status] || status.replace(/_/g, " ");
}
