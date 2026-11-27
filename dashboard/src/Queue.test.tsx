import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Queue } from "./Queue";
import { json, stubFetch } from "./testing";
import type { QueueRow } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const row = (overrides: Partial<QueueRow>): QueueRow => ({
  claim_id: "CLM-1001",
  customer_name: "Maya Patel",
  claim_type: "trip_delay",
  amount_claimed: 420,
  state: "waiting",
  decision: null,
  payout: null,
  ...overrides,
});

describe("Queue", () => {
  it("lists each claim with its state and decision", async () => {
    stubFetch({
      "/api/claims": json([
        row({}),
        row({
          claim_id: "CLM-1002",
          state: "waiting for sign-off",
          decision: "approve",
          payout: 1100,
          amount_claimed: 1150,
        }),
        row({
          claim_id: "CLM-1003",
          state: "decided",
          decision: "decline",
          payout: 0,
        }),
      ]),
    });
    render(<Queue />);
    expect(await screen.findAllByText("Maya Patel")).toHaveLength(3);
    expect(screen.getByText("Waiting for sign-off")).toBeDefined();
    expect(screen.getByText("Approve, $1,100.00")).toBeDefined();
    expect(screen.getByText("Decline")).toBeDefined();
    expect(screen.getByText("None yet")).toBeDefined();
    expect(screen.getAllByText("$420.00")).toHaveLength(2);
  });

  it("works the queue and reports how many claims are waiting", async () => {
    const mock = stubFetch({
      "/api/claims": json([row({}), row({ claim_id: "CLM-1002" })]),
      "POST /api/runs": json({ waiting: 2 }, 202),
    });
    render(<Queue />);
    const button = await screen.findByRole("button", {
      name: "Work the queue",
    });
    fireEvent.click(button);
    expect(
      await screen.findByText("Working through 2 waiting claims."),
    ).toBeDefined();
    expect(mock).toHaveBeenCalledWith(
      "/api/runs",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("disables the button when no claim is waiting", async () => {
    stubFetch({
      "/api/claims": json([row({ state: "decided", decision: "refer" })]),
    });
    render(<Queue />);
    const button = await screen.findByRole("button", {
      name: "Work the queue",
    });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows a failure to work the queue", async () => {
    stubFetch({
      "/api/claims": json([row({})]),
      "POST /api/runs": json({ detail: "The queue is busy." }, 409),
    });
    render(<Queue />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Work the queue" }),
    );
    expect(await screen.findByRole("alert")).toBeDefined();
    expect(screen.getByText("The queue is busy.")).toBeDefined();
  });

  it("shows a failure to load the queue", async () => {
    stubFetch({});
    render(<Queue />);
    expect(await screen.findByRole("alert")).toBeDefined();
  });

  it("refreshes while a claim is in progress", async () => {
    const mock = stubFetch({
      "/api/claims": json([row({ state: "in progress" })]),
    });
    render(<Queue />);
    await screen.findAllByText("Maya Patel");
    await vi.waitFor(
      () => {
        expect(mock.mock.calls.length).toBeGreaterThan(1);
      },
      { timeout: 4000 },
    );
  });
});
