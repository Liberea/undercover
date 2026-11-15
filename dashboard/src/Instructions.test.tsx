import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Instructions } from "./Instructions";
import { stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the instructions for the queue and for a claim, read only", async () => {
  stubApi({
    "GET /api/instructions": {
      queue: "You run the claims queue.",
      claim: "You decide one claim.",
    },
  });
  render(<Instructions />);
  const queue = await screen.findByRole("region", {
    name: "Working the queue",
  });
  expect(within(queue).getByText("You run the claims queue.")).toBeDefined();
  const claim = screen.getByRole("region", { name: "Working a claim" });
  expect(within(claim).getByText("You decide one claim.")).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
});
