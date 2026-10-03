import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";
import { QueryClientProvider } from "@tanstack/lit-query";
import { queryClient } from "@api/query-client";
import "@app/prompster-app";
import "./style.css";

class AppQueryProvider extends QueryClientProvider {
  constructor() {
    super();
    this.client = queryClient;
  }
}
customElements.define("app-query-provider", AppQueryProvider);
