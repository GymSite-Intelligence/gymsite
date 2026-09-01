import { Container, getContainer } from "@cloudflare/containers";

export class GymSiteApiContainer extends Container<Env> {
  defaultPort = 8000;
  requiredPorts = [8000];
  sleepAfter = "10m";
  enableInternet = true;
  envVars = {
    CONTAINER_POC: "1",
    RUN_QUEUE_WORKER: "0",
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = getContainer(env.GYMSITE_API, "poc");
    return container.fetch(request);
  },
} satisfies ExportedHandler<Env>;
