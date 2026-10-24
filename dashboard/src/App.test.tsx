import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { claim, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  window.location.hash = "";
});

function goTo(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

it("opens on the claims queue", async () => {
  stubApi({ "GET /api/claims": [] });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
  const queue = screen.getByRole("link", { name: "Queue" });
  expect(queue.getAttribute("aria-current")).toBe("page");
});

it("follows the URL to a claim's page within the queue", async () => {
  stubApi({ "GET /api/claims/CLM-1001": claim({}) });
  render(<App />);
  goTo("#/claims/CLM-1001");
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();
  const queue = screen.getByRole("link", { name: "Queue" });
  expect(queue.getAttribute("aria-current")).toBe("page");
});

it("follows the URL to the instructions", async () => {
  stubApi({ "GET /api/instructions": { text: "You are the agent." } });
  render(<App />);
  goTo("#/instructions");
  expect(await screen.findByText("You are the agent.")).toBeDefined();
  const link = screen.getByRole("link", { name: "Instructions" });
  expect(link.getAttribute("aria-current")).toBe("page");
});

it("switches between dark and light mode and remembers it", () => {
  stubApi({ "GET /api/claims": [] });
  render(<App />);
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.click(screen.getByRole("button", { name: "Light mode" }));
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(localStorage.getItem("undercover-theme")).toBe("light");
  expect(screen.getByRole("button", { name: "Dark mode" })).toBeDefined();
});
