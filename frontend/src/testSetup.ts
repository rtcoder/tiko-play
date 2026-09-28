import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
afterEach(cleanup);

import { setLanguage } from "./i18n";
beforeEach(() => setLanguage("pl"));
