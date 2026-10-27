import { defineAgent } from "@grok/agent-sdk";

export default defineAgent({
  // A hosted deploy may only reach the hosts listed here, and reads the API key
  // from a deployment secret: agent-sdk secret set trendsagi-agent TRENDSAGI_API_KEY
  hosting: {
    egressDomains: ["api.trendsagi.com"],
    secretNames: ["TRENDSAGI_API_KEY"],
  },
});
