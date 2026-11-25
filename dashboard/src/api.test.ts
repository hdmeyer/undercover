import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, errorMessage, getJson, getText, postJson } from "./api";
import { json, stubFetch, text } from "./testing";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api", () => {
  it("reads JSON", async () => {
    stubFetch({ "/api/claims": json([{ claim_id: "CLM-1001" }]) });
    expect(await getJson("/api/claims")).toEqual([{ claim_id: "CLM-1001" }]);
  });

  it("sends JSON on a POST", async () => {
    const mock = stubFetch({ "POST /api/x": json({ ok: true }) });
    await postJson("/api/x", { amount: 5 });
    const init = mock.mock.calls[0]?.[1];
    expect(init?.body).toBe(JSON.stringify({ amount: 5 }));
    expect(init?.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("shows the backend's reason when a request is refused", async () => {
    stubFetch({
      "POST /api/x": json({ detail: "Waiting for sign-off." }, 409),
    });
    await expect(postJson("/api/x")).rejects.toThrow("Waiting for sign-off.");
  });

  it("shows the status when the reason is not text", async () => {
    stubFetch({ "POST /api/x": json({ detail: [] }, 422) });
    await expect(postJson("/api/x")).rejects.toThrow(
      "The request failed (422).",
    );
  });

  it("reads plain text, and reports a failed read", async () => {
    stubFetch({ "/api/wording": text("Policy") });
    expect(await getText("/api/wording")).toBe("Policy");
    stubFetch({ "/api/wording": json({}, 500) });
    await expect(getText("/api/wording")).rejects.toBeInstanceOf(ApiError);
  });

  it("describes any error", () => {
    expect(errorMessage(new Error("Offline."))).toBe("Offline.");
    expect(errorMessage("nope")).toBe("Something went wrong.");
  });
});
