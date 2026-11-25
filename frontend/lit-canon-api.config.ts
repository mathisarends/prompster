import { defineConfig } from "lit-canon-api";

export default defineConfig({
  input: process.env.OPENAPI_SPEC_PATH ?? "./openapi.json",
  output: "./src/api/generated",
  request: {
    path: "./src/api/request.ts",
    exports: ["ApiError"],
    typeExports: ["ApiProblem", "ApiRequestOptions"],
  },
  excludeTags: ["system"],
  mutationOperations: ["googleLogin", "spotifyLogin", "spotifyConnect"],
});
