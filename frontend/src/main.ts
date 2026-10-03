import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import { QueryClientProvider } from "@tanstack/lit-query";
import { queryClient } from "@api/query-client";
import { initializeLocale } from "@shared/i18n";
import "./style.css";

class AppQueryProvider extends QueryClientProvider {
  constructor() {
    super();
    this.client = queryClient;
  }
}
customElements.define("app-query-provider", AppQueryProvider);

// Define the app only after localization is ready, avoiding a flash of German text.
void initializeLocale().then(() => import("@app/prompster-app"));
