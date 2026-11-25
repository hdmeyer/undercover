import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ClaimPage } from "./ClaimPage";
import { json, stubFetch } from "./testing";
import type { ClaimEvent, ClaimView } from "./types";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function view(overrides: Partial<ClaimView>): ClaimView {
  return {
    claim: {
      claim_id: "CLM-1002",
      policy_id: "POL-2002",
      claim_type: "baggage",
      submitted_on: "2026-06-24",
      incident_date: "2026-06-18",
      incident_location: "Lisbon, Portugal",
      summary: "Bag delayed",
      story: "My checked bag arrived two days late.",
      items: [{ description: "Clothes", category: "clothing", amount: 1150 }],
      amount_claimed: 1150,
      documents: [
        {
          name: "Carrier report",
          type: "carrier_report",
          content: "Late bag.",
        },
      ],
    },
    customer: {
      customer_id: "CUS-3002",
      name: "Ravi Shah",
      customer_since: "2024-01-01",
      previous_claims: [],
    },
    policy: {
      policy_id: "POL-2002",
      plan: "premium",
      add_ons: [],
      trip: {
        destination: "Lisbon, Portugal",
        departs_on: "2026-06-10",
        returns_on: "2026-06-20",
      },
      travelers: ["Ravi Shah"],
    },
    plan: { plan: "premium", name: "UnderCover Premium" },
    add_ons: [],
    state: "waiting",
    decision: null,
    payments: [],
    paid_total: 0,
    ...overrides,
  };
}

const approved = {
  decision: "approve" as const,
  payout: 1100,
  explanation: "Covered as delayed baggage.",
  policy_section: "5",
  decided_at: "2026-11-25T10:00:00+00:00",
  signed_off_at: null,
};

const events: ClaimEvent[] = [
  {
    kind: "step",
    text: "Called get_claim_for_agent with {}.",
    created_at: "2026-11-25T10:00:00+00:00",
  },
  {
    kind: "decision",
    text: "Approve: payout $1,100.00.",
    created_at: "2026-11-25T10:01:00+00:00",
  },
];

describe("ClaimPage", () => {
  it("shows the claim, the policy and the customer's name", async () => {
    stubFetch({
      "/api/claims/CLM-1002": json(view({})),
      "/api/claims/CLM-1002/events": json([]),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    expect(
      await screen.findByRole("heading", { name: "Ravi Shah" }),
    ).toBeDefined();
    expect(
      screen.getByText("My checked bag arrived two days late."),
    ).toBeDefined();
    expect(screen.getByText("UnderCover Premium")).toBeDefined();
    expect(screen.getByText("No decision yet.")).toBeDefined();
    expect(screen.getByText("Nothing logged yet.")).toBeDefined();
  });

  it("runs the agent when the claim is waiting", async () => {
    const mock = stubFetch({
      "/api/claims/CLM-1002": json(view({})),
      "/api/claims/CLM-1002/events": json([]),
      "POST /api/claims/CLM-1002/run": json({ state: "in progress" }, 202),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
    await vi.waitFor(() => {
      expect(mock).toHaveBeenCalledWith(
        "/api/claims/CLM-1002/run",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("blocks payment until a handler signs off an over-limit payout", async () => {
    const mock = stubFetch({
      "/api/claims/CLM-1002": json(
        view({ state: "waiting for sign-off", decision: approved }),
      ),
      "/api/claims/CLM-1002/events": json(events),
      "POST /api/claims/CLM-1002/sign-off": json({ state: "decided" }),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    expect(await screen.findByText(/waits for a handler/)).toBeDefined();
    const pay = screen.getByRole("button", { name: "Pay $1,100.00" });
    expect(pay).toHaveProperty("disabled", true);
    fireEvent.click(screen.getByRole("button", { name: "Sign off" }));
    await vi.waitFor(() => {
      expect(mock).toHaveBeenCalledWith(
        "/api/claims/CLM-1002/sign-off",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("pays the rest of an approved payout once it is decided", async () => {
    const mock = stubFetch({
      "/api/claims/CLM-1002": json(
        view({
          state: "decided",
          decision: { ...approved, payout: 500 },
          payments: [{ amount: 200, paid_at: "2026-11-25T10:05:00+00:00" }],
          paid_total: 200,
        }),
      ),
      "/api/claims/CLM-1002/events": json(events),
      "POST /api/claims/CLM-1002/payments": json({ state: "decided" }),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    const pay = await screen.findByRole("button", { name: "Pay $300.00" });
    fireEvent.click(pay);
    await vi.waitFor(() => {
      expect(mock).toHaveBeenCalledWith(
        "/api/claims/CLM-1002/payments",
        expect.objectContaining({ body: JSON.stringify({ amount: 300 }) }),
      );
    });
  });

  it("shows the activity log in order", async () => {
    stubFetch({
      "/api/claims/CLM-1002": json(
        view({ state: "decided", decision: approved }),
      ),
      "/api/claims/CLM-1002/events": json(events),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    expect(
      await screen.findByText("Called get_claim_for_agent with {}."),
    ).toBeDefined();
    expect(screen.getByText("Approve: payout $1,100.00.")).toBeDefined();
  });

  it("shows a refused action", async () => {
    stubFetch({
      "/api/claims/CLM-1002": json(
        view({ state: "decided", decision: approved }),
      ),
      "/api/claims/CLM-1002/events": json([]),
      "POST /api/claims/CLM-1002/payments": json({ detail: "Too much." }, 409),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Pay $1,100.00" }),
    );
    expect(await screen.findByText("Too much.")).toBeDefined();
  });

  it("shows the earlier claims of the customer", async () => {
    stubFetch({
      "/api/claims/CLM-1002": json(
        view({
          customer: {
            customer_id: "CUS-3002",
            name: "Ravi Shah",
            customer_since: "2024-01-01",
            previous_claims: [
              {
                claim_id: "CLM-0412",
                filed_on: "2024-08-19",
                claim_type: "baggage_delay",
                summary: "Bag late in Lisbon",
                outcome: "approved",
                amount_paid: 140,
              },
            ],
          },
        }),
      ),
      "/api/claims/CLM-1002/events": json([]),
    });
    render(<ClaimPage claimId="CLM-1002" />);
    expect(await screen.findByText("CLM-0412")).toBeDefined();
    expect(screen.getByText(/Bag late in Lisbon/)).toBeDefined();
  });

  it("shows a message while the claim loads or cannot be found", async () => {
    stubFetch({});
    render(<ClaimPage claimId="CLM-9999" />);
    expect(await screen.findByText(/No stub for/)).toBeDefined();
  });
});
