import { useEffect, useState } from "react";
import { ClaimPage } from "./ClaimPage";
import { getJson } from "./api";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { parseRoute, type Route } from "./route";

function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    parseRoute(window.location.hash),
  );

  useEffect(() => {
    const onChange = () => {
      setRoute(parseRoute(window.location.hash));
    };
    window.addEventListener("hashchange", onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);

  return route;
}

function Page({ route }: { readonly route: Route }) {
  switch (route.name) {
    case "queue":
      return <Queue />;
    case "claim":
      return <ClaimPage key={route.claimId} claimId={route.claimId} />;
    case "instructions":
      return <Instructions />;
  }
}

function BackendStatus() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    void getJson<{ status: string }>("/api/health")
      .then(() => "up")
      .catch(() => "down")
      .then(setStatus);
  }, []);

  return <p className="status">Backend: {status}</p>;
}

export function App() {
  const route = useRoute();
  return (
    <>
      <header className="site-header">
        <a className="brand" href="#/">
          UnderCover
        </a>
        <span className="tagline">Travel insurance claims</span>
        <nav>
          <a href="#/">Queue</a>
          <a href="#/instructions">Agent instructions</a>
        </nav>
      </header>
      <main>
        <Page route={route} />
      </main>
      <footer>
        <BackendStatus />
      </footer>
    </>
  );
}
