import { test } from "node:test";
import assert from "node:assert/strict";
import { apiFetch, ApiError } from "../src/api/request.ts";

test("serializes repeated query parameters, preserves false and cookies", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async (url: string, options: RequestInit) => {
    assert.equal(
      url,
      "http://127.0.0.1:8000/search?types=track&types=artist&limit=0&enabled=false",
    );
    assert.equal(options.credentials, "include");
    return Response.json({ ok: true });
  });
  assert.deepEqual(
    await apiFetch("/search", {
      query: { types: ["track", "artist"], limit: 0, enabled: false, absent: undefined },
    }),
    { ok: true },
  );
  fetch.mock.restore();
});
test("sends JSON once and does not force a content type for multipart", async (t) => {
  const requests: RequestInit[] = [];
  t.mock.method(globalThis, "fetch", async (_url: string, options: RequestInit) => {
    requests.push(options);
    return new Response(null, { status: 204 });
  });
  await apiFetch("/json", { method: "POST", body: { title: "Musik" } });
  const form = new FormData();
  form.append("file", new Blob(["image"]), "image.png");
  await apiFetch("/upload", { method: "POST", body: form });
  assert.equal(requests[0].body, '{"title":"Musik"}');
  assert.equal(new Headers(requests[0].headers).get("content-type"), "application/json");
  assert.equal(new Headers(requests[1].headers).has("content-type"), false);
  assert.equal(requests[1].body, form);
});
test("keeps PDF bytes intact and surfaces problem details", async (t) => {
  t.mock.method(globalThis, "fetch", async (url: string) =>
    url.endsWith("/pdf")
      ? new Response(new Uint8Array([37, 80, 68, 70, 255, 0]), {
          headers: { "content-type": "application/pdf" },
        })
      : Response.json(
          { type: "about:blank", title: "Conflict", status: 409, detail: "Deck is full" },
          { status: 409, headers: { "content-type": "application/problem+json" } },
        ),
  );
  const blob = await apiFetch<Blob>("/pdf");
  assert.deepEqual(
    new Uint8Array(await blob.arrayBuffer()),
    new Uint8Array([37, 80, 68, 70, 255, 0]),
  );
  await assert.rejects(
    apiFetch("/error"),
    (error: unknown) =>
      error instanceof ApiError && error.status === 409 && error.problem?.detail === "Deck is full",
  );
});
test("concurrent 401s share a single refresh and retry once", async (t) => {
  let refreshes = 0;
  let authenticated = false;
  t.mock.method(globalThis, "fetch", async (url: string) => {
    if (url.endsWith("/auth/refresh")) {
      refreshes++;
      await new Promise((resolve) => setTimeout(resolve, 15));
      authenticated = true;
      return new Response(null, { status: 204 });
    }
    return authenticated ? Response.json({ id: 1 }) : new Response(null, { status: 401 });
  });
  await Promise.all([apiFetch("/one"), apiFetch("/two")]);
  assert.equal(refreshes, 1);
});
test("a rejected refresh cannot recurse", async (t) => {
  let requests = 0;
  t.mock.method(globalThis, "fetch", async () => {
    requests++;
    return new Response(null, { status: 401 });
  });
  await assert.rejects(
    apiFetch("/protected"),
    (error: unknown) => error instanceof ApiError && error.status === 401,
  );
  assert.equal(requests, 2);
});

test("an aborted request is not retried after the cookie refresh", async (t) => {
  const controller = new AbortController();
  const fetch = t.mock.method(globalThis, "fetch", async (url: string) => {
    if (url.endsWith("/auth/refresh")) {
      controller.abort();
      return new Response(null, { status: 204 });
    }
    return new Response(null, { status: 401 });
  });

  await assert.rejects(apiFetch("/protected", { signal: controller.signal }), {
    name: "AbortError",
  });
  assert.equal(fetch.mock.callCount(), 2);
});
