/**
 * GET  /api/room?code=AB12-CD34   -> { code, state }
 * POST /api/room  { state }       -> { code, state }   (creates a new room)
 */

const kv = require("./_kv.js");
const room = require("./_room.js");

function readBody(req) {
  if (!req.body) return {};
  if (typeof req.body === "string") {
    try { return JSON.parse(req.body); } catch { return {}; }
  }
  return req.body;
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (!kv.configured()) {
    return res.status(503).json({
      error: "storage_not_configured",
      message:
        "No Redis credentials. Add a Redis/KV integration in the Vercel " +
        "dashboard so KV_REST_API_URL and KV_REST_API_TOKEN are set.",
    });
  }

  try {
    if (req.method === "GET") {
      const code = room.normaliseCode(req.query && req.query.code);
      if (!code) return res.status(400).json({ error: "bad_code" });

      const state = await room.load(code);
      if (!state) return res.status(404).json({ error: "no_such_room" });

      await kv.pipeline(kv.touch(Object.values(room.keys(code))));
      return res.status(200).json({ code, state });
    }

    if (req.method === "POST") {
      const { state } = readBody(req);
      const code = room.newCode();
      await kv.pipeline(room.seedCommands(code, state));
      return res.status(201).json({ code, state: await room.load(code) });
    }

    res.setHeader("Allow", "GET, POST");
    return res.status(405).json({ error: "method_not_allowed" });
  } catch (err) {
    console.error("room handler failed:", err);
    return res.status(500).json({ error: "server_error", message: String(err.message || err) });
  }
};
