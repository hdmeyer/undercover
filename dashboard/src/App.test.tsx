import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { json, stubFetch, text } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

describe("App", () => {
  it("shows that the backend is up", async () => {
    stubFetch({
      "/api/health": json({ status: "ok" }),
      "/api/claims": json([]),
    });
    render(<App />);
    expect(await screen.findByText("Backend: up")).toBeDefined();
  });

  it("shows that the backend is down", async () => {
    stubFetch({});
    render(<App />);
    expect(await screen.findByText("Backend: down")).toBeDefined();
  });

  it("switches screens when the address changes", async () => {
    stubFetch({
      "/api/health": json({ status: "ok" }),
      "/api/claims": json([]),
      "/api/agent/instructions": text("Read only instructions."),
    });
    render(<App />);
    await screen.findByText("Backend: up");
    act(() => {
      window.location.hash = "#/instructions";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(await screen.findByText("Read only instructions.")).toBeDefined();
  });
});
