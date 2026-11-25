const { app } = require("@azure/functions");

/** GET /api/health — liveness for SWA and optional monitoring checks. */
app.http("health", {
  methods: ["GET"],
  authLevel: "anonymous",
  route: "health",
  handler: async () => ({
    status: 200,
    jsonBody: {
      status: "ok",
      service: "azure-ai-hub",
    },
  }),
});