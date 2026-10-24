import { useEffect, useState } from "react";

export type Route =
  | { view: "queue" }
  | { view: "claim"; claimId: string }
  | { view: "instructions" };

export function parseRoute(hash: string): Route {
  const claim = /^#\/claims\/(.+)$/.exec(hash);
  if (claim) return { view: "claim", claimId: decodeURIComponent(claim[1]) };
  if (hash === "#/instructions") return { view: "instructions" };
  return { view: "queue" };
}

export function useRoute(): Route {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);
  return parseRoute(hash);
}

export interface Polled<T> {
  data: T | undefined;
  failed: boolean;
}

/**
 * Load data now and again every `everyMs`, or only once when it's null.
 * `load` must keep its identity between renders.
 */
export function usePolling<T>(load: () => Promise<T>, everyMs: number | null) {
  const [polled, setPolled] = useState<Polled<T>>({
    data: undefined,
    failed: false,
  });
  useEffect(() => {
    let active = true;
    const tick = () => {
      load().then(
        (data) => {
          if (active) setPolled({ data, failed: false });
        },
        () => {
          if (active) setPolled((last) => ({ ...last, failed: true }));
        },
      );
    };
    tick();
    const timer = everyMs === null ? undefined : setInterval(tick, everyMs);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [load, everyMs]);
  return polled;
}

export type Theme = "dark" | "light";
const THEME_KEY = "undercover-theme";

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() =>
    localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);
  const toggle = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };
  return [theme, toggle];
}
