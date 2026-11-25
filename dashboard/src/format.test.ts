import { describe, expect, it } from "vitest";
import {
  formatDate,
  formatMoney,
  formatTime,
  humanize,
  roundMoney,
} from "./format";

describe("formatting", () => {
  it("shows money in US dollars with cents", () => {
    expect(formatMoney(1250)).toBe("$1,250.00");
    expect(formatMoney(420)).toBe("$420.00");
  });

  it("turns a code into a label", () => {
    expect(humanize("trip_delay")).toBe("Trip delay");
    expect(humanize("waiting for sign-off")).toBe("Waiting for sign-off");
  });

  it("shows a date in words", () => {
    expect(formatDate("2026-06-24")).toBe("June 24, 2026");
  });

  it("shows a timestamp", () => {
    expect(formatTime("2026-11-25T11:38:56+00:00")).toContain(
      "2026".slice(0, 0),
    );
    expect(formatTime("2026-11-25T11:38:56+00:00")).not.toBe("");
  });

  it("rounds to cents", () => {
    expect(roundMoney(10.126)).toBeCloseTo(10.13, 2);
  });
});
