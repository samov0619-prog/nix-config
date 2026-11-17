// Synthetic review target: implementation predates the changed API contract.
export function badgeTone(result) {
  return result === 1 ? "green" : "red";
}
