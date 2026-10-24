import { expect, it } from "vitest";
import { date, label, money } from "./format";
import { parseRoute } from "./hooks";

it("formats money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
});

it("formats dates without shifting the day", () => {
  expect(date("2026-06-24")).toBe("Jun 24, 2026");
});

it("turns codes into labels", () => {
  expect(label("waiting_for_sign_off")).toBe("Waiting for sign off");
  expect(label("trip_delay")).toBe("Trip delay");
});

it("reads the view from the URL", () => {
  expect(parseRoute("")).toEqual({ view: "queue" });
  expect(parseRoute("#/claims/CLM-1001")).toEqual({
    view: "claim",
    claimId: "CLM-1001",
  });
  expect(parseRoute("#/instructions")).toEqual({ view: "instructions" });
});
