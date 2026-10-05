import { useEffect, type ReactNode } from "react";
import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { EmptyState } from "./components/ui";
import { DemoProvider, useDemo } from "./demo/DemoContext";
import type { CanonicalDemo } from "./demo/canonical";
import type { DriveRecord } from "./demo/discovery";
import { DemoSetup } from "./pages/DemoSetup";
import { Home } from "./pages/Home";
import { Ask } from "./pages/Ask";
import { Drive } from "./pages/Drive";
import { Vehicle } from "./pages/Vehicle";
import { WhyRange } from "./pages/WhyRange";
import { WhatIf } from "./pages/WhatIf";
import { Cost } from "./pages/Cost";

export function App() {
  return (
    <BrowserRouter>
      <DemoProvider>
        <DemoGate />
      </DemoProvider>
    </BrowserRouter>
  );
}

/** Routes are reachable only once canonical demo data is verified. Otherwise the setup screen shows. */
function DemoGate() {
  const demo = useDemo();
  if (demo.status === "ready" && demo.hero) {
    return <ReadyRoutes hero={demo.hero} drives={demo.drives} />;
  }
  return <DemoSetup />;
}

function ReadyRoutes({ hero, drives }: { hero: CanonicalDemo; drives: DriveRecord[] }) {
  return (
    <Routes>
      <Route path="/" element={<Screen><Home hero={hero} drives={drives} /></Screen>} />
      <Route path="/ask" element={<Screen title="Ask"><Ask /></Screen>} />
      <Route path="/drive" element={<Screen title="Drive"><Drive hero={hero} drives={drives} /></Screen>} />
      <Route path="/vehicle" element={<Screen title="Vehicle"><Vehicle hero={hero} /></Screen>} />
      <Route path="/why-range" element={<Screen title="Why range"><WhyRange hero={hero} /></Screen>} />
      <Route path="/what-if" element={<Screen title="What if"><WhatIf hero={hero} /></Screen>} />
      <Route path="/cost" element={<Screen title="Cost"><Cost hero={hero} /></Screen>} />
      <Route
        path="*"
        element={
          <Screen title="Not found">
            <EmptyState title="Page not found" body="This screen does not exist in VehicleGPT.">
              <Link className="btn btn--secondary btn--block" to="/">Go to Home</Link>
            </EmptyState>
          </Screen>
        }
      />
    </Routes>
  );
}

/** Wraps each screen in the shell and moves focus to the content on navigation. */
function Screen({ title, children }: { title?: string; children: ReactNode }) {
  const location = useLocation();
  useEffect(() => {
    const main = document.getElementById("main");
    if (main && location.hash === "") main.focus({ preventScroll: true });
    if (location.hash) {
      document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: "start" });
    }
  }, [location.pathname, location.hash]);
  return <AppShell title={title}>{children}</AppShell>;
}
