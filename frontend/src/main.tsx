import "bootstrap/dist/css/bootstrap-grid.min.css";
import "./styles.css";
import "./theme.css";
import "./auth.css";
import "./task-detail.css";
import "./management.css";
import "./features.css";
import "./studio.css";
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
