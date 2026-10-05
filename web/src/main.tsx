import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { OperationsDashboard } from "./OperationsDashboard";
import "./style.css";

const root = document.getElementById("root");
if (!root) throw new Error("Application root missing");
createRoot(root).render(
  <StrictMode>
    {window.location.pathname === "/operations" ? (
      <OperationsDashboard />
    ) : (
      <App />
    )}
  </StrictMode>,
);
