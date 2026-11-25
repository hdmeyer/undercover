import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Instructions } from "./Instructions";
import { stubFetch, text } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Instructions", () => {
  it("shows the agent's instructions, read only", async () => {
    stubFetch({
      "/api/agent/instructions": text("You are the UnderCover Agent."),
    });
    render(<Instructions />);
    expect(
      await screen.findByText("You are the UnderCover Agent."),
    ).toBeDefined();
    expect(screen.getByText("These are read only.")).toBeDefined();
  });

  it("shows a failure to load them", async () => {
    stubFetch({});
    render(<Instructions />);
    expect(await screen.findByRole("alert")).toBeDefined();
  });
});
