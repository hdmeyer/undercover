import { describe, expect, it } from "vitest";
import { parseRoute } from "./route";

describe("parseRoute", () => {
  it("opens the queue by default", () => {
    expect(parseRoute("")).toEqual({ name: "queue" });
    expect(parseRoute("#/")).toEqual({ name: "queue" });
    expect(parseRoute("#/claims/")).toEqual({ name: "queue" });
  });

  it("opens a claim", () => {
    expect(parseRoute("#/claims/CLM-1001")).toEqual({
      name: "claim",
      claimId: "CLM-1001",
    });
  });

  it("opens the instructions", () => {
    expect(parseRoute("#/instructions")).toEqual({ name: "instructions" });
  });
});
