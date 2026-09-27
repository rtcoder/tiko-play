import { it, expect, vi, afterEach } from "vitest";
import { bootstrapSession, request } from "./client";
afterEach(() => vi.unstubAllGlobals());
it("removes fragment before token exchange and recovers session on refresh", async () => {
  history.replaceState(null, "", "/#token=secret");
  const fetch = vi.fn(async () => {
    expect(location.hash).toBe("");
    return new Response(JSON.stringify({ csrf_token: "csrf" }), {
      status: 200,
    });
  });
  vi.stubGlobal("fetch", fetch);
  await bootstrapSession();
  expect(fetch.mock.calls).toHaveLength(1);
  await bootstrapSession();
  expect(fetch.mock.calls).toHaveLength(2);
});
it("surfaces structured API errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({ code: "revision_conflict", message: "Konflikt" }),
          { status: 409 },
        ),
    ),
  );
  await expect(request("/api/config")).rejects.toMatchObject({
    code: "revision_conflict",
    status: 409,
  });
});
