import "@fontsource-variable/inter";
import "@fontsource-variable/geist-mono";
// Music card faces, the same cuts the printable deck embeds.
import "@fontsource/barlow-condensed/700.css";
import "@fontsource/barlow-condensed/500-italic.css";
import "@fontsource/archivo-black/400.css";
import "@fontsource/space-mono/700.css";
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
