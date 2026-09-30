import { createRoot } from "react-dom/client";
import App from "./App";
import Overlay from "./overlay/Overlay";
import "./styles.css";
import "./styles-glass.css";
import "./overlay/overlay.css";
const overlay = location.pathname === "/overlay";
if (overlay) document.documentElement.classList.add("overlay-page");
createRoot(document.getElementById("root")!).render(
  overlay ? <Overlay /> : <App />,
);
