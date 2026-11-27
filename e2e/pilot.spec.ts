import { expect, test } from "@playwright/test";

test("the queue lists all twenty-five claims", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.locator("tbody tr")).toHaveCount(25);
});

test("a claim shows its story and that it has no decision yet", async ({
  page,
}) => {
  await page.goto("/#/claims/CLM-1001");
  await expect(page.getByRole("heading", { name: "Maya Patel" })).toBeVisible();
  await expect(page.getByText("My flight home from Rome")).toBeVisible();
  await expect(page.getByText("No decision yet.")).toBeVisible();
});

test("the agent's instructions are shown read only", async ({ page }) => {
  await page.goto("/#/instructions");
  await expect(page.getByText("You are the UnderCover Agent.")).toBeVisible();
});

test("an over-limit payout is paid only after a handler signs it off", async ({
  page,
  request,
}) => {
  const decided = await request.post("/api/claims/CLM-1002/decision", {
    data: {
      decision: "approve",
      payout: 1100,
      explanation: "Covered as delayed baggage.",
      policy_section: "5",
    },
  });
  expect(decided.ok()).toBeTruthy();

  await page.goto("/#/claims/CLM-1002");
  await expect(
    page.getByText("Waiting for sign-off", { exact: true }),
  ).toBeVisible();
  const pay = page.getByRole("button", { name: "Pay $1,100.00" });
  await expect(pay).toBeDisabled();

  await page.getByRole("button", { name: "Sign off" }).click();
  await expect(pay).toBeEnabled();
  await pay.click();
  await expect(page.getByText(/Paid \$1,100\.00 so far/)).toBeVisible();
});
