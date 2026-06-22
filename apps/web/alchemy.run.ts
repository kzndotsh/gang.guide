import "dotenv/config";
import alchemy from "alchemy";
import { SvelteKit } from "alchemy/cloudflare";

const app = await alchemy("gang-guide");

await SvelteKit("website", {
  name: `gang-guide-${app.stage}`,
  domains: ["gang.guide"],
  adopt: true,
});

await app.finalize();
