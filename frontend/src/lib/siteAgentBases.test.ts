import { describe, expect, test } from "bun:test";
import { resolveSiteAgentBases } from "./siteAgentBases";

describe("resolveSiteAgentBases", () => {
  test("cloudflare ignora VITE_API_BASE Hetzner — chat same-origin", () => {
    expect(
      resolveSiteAgentBases({
        provider: "cloudflare",
        viteApiBase: "https://api.getgymsite.com.br",
        origin: "https://gymsite.com.br",
      }),
    ).toEqual(["https://gymsite.com.br"]);
  });

  test("sem provider usa API A0–A9", () => {
    expect(
      resolveSiteAgentBases({
        viteApiBase: "https://api.getgymsite.com.br",
        origin: "https://gymsite.com.br",
      }),
    ).toEqual(["https://api.getgymsite.com.br"]);
  });
});
