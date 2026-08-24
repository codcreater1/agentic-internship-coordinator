// Completion-queue tabs, in the order a coordinator works: things they can act
// on first, things waiting on somebody else after.
//
// Kept out of the component file so that file exports only a component — React
// Fast Refresh cannot handle a module that mixes the two.
export const COMPLETION_TABS = [
  {
    key: "toSign",
    label: "To sign",
    match: (s) => s.status === "approved" || s.status === "pending",
    empty: {
      title: "Nothing waiting on you",
      body: "Packages that pass their checks appear here for signature.",
    },
  },
  {
    key: "waiting",
    label: "With student",
    match: (s) => s.status === "request_clarification" || s.status === "rejected",
    empty: {
      title: "Nothing outstanding",
      body: "Submissions asked to be corrected and resent appear here.",
    },
  },
  {
    key: "signed",
    label: "Signed",
    match: (s) => s.status === "signed",
    empty: {
      title: "No certificates yet",
      body: "Issued completion certificates land here.",
    },
  },
];

export function tabFor(key) {
  return COMPLETION_TABS.find((t) => t.key === key) || COMPLETION_TABS[0];
}

export function countsByTab(submissions) {
  return COMPLETION_TABS.reduce(
    (acc, t) => ({ ...acc, [t.key]: submissions.filter(t.match).length }),
    {},
  );
}
