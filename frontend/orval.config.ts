import { defineConfig } from "orval";

export default defineConfig({
  prompster: {
    input: {
      target: "./openapi.json",
    },
    hooks: {
      afterAllFilesWrite: "npm run postprocess:api",
    },
    output: {
      mode: "tags-split",
      target: "src/api/generated",
      schemas: "src/api/generated/model",
      client: "react-query",
      httpClient: "axios",
      clean: true,
      formatter: "prettier",
      override: {
        mutator: {
          path: "./src/api/http-client.ts",
          name: "customInstance",
        },
        query: {
          useQuery: true,
          useInfinite: true,
          useMutation: true,
          shouldExportQueryKey: true,
          shouldExportHttpClient: true,
        },
      },
    },
  },
});
