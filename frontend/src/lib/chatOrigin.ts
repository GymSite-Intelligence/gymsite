/** CF Pages preview = `{hash}.gym-insight-hub.pages.dev`. Turnstile widget só
 *  valida hostnames cadastrados no painel CF — hash preview não entra → 403. */
const PREVIEW_HOST =
  /^[a-f0-9]{8}\.(gym-insight-hub|gymsite(-3p0)?)\.pages\.dev$/i;

export const CHAT_PRODUCTION_URL = "https://www.gymsite.com.br/degustacao";

export function isDeploymentPreviewHost(hostname = typeof window !== "undefined" ? window.location.hostname : ""): boolean {
  return PREVIEW_HOST.test(hostname);
}
