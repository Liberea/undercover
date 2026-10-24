import { ClaimPage } from "./ClaimPage";
import { useRoute, useTheme, type Route } from "./hooks";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";

export function App() {
  const route = useRoute();
  const [theme, toggleTheme] = useTheme();
  const section = route.view === "instructions" ? "instructions" : "queue";
  const current = (view: Route["view"]) =>
    section === view ? "page" : undefined;
  return (
    <div className="page">
      <header className="topbar">
        <a className="brand" href="#/">
          UnderCover
        </a>
        <nav className="nav" aria-label="Main">
          <a href="#/" aria-current={current("queue")}>
            Queue
          </a>
          <a href="#/instructions" aria-current={current("instructions")}>
            Instructions
          </a>
        </nav>
        <button
          type="button"
          className="button button-quiet"
          onClick={toggleTheme}
        >
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </header>
      <main>
        <View route={route} />
      </main>
    </div>
  );
}

function View({ route }: Readonly<{ route: Route }>) {
  if (route.view === "claim") return <ClaimPage claimId={route.claimId} />;
  if (route.view === "instructions") return <Instructions />;
  return <Queue />;
}
