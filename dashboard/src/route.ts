export type Route =
  | { name: "queue" }
  | { name: "claim"; claimId: string }
  | { name: "instructions" };

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#\/?/, "");
  if (path === "instructions") {
    return { name: "instructions" };
  }
  const claimId = /^claims\/([^/]+)$/.exec(path)?.[1];
  if (claimId !== undefined) {
    return { name: "claim", claimId: decodeURIComponent(claimId) };
  }
  return { name: "queue" };
}
