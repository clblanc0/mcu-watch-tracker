/**
 * POST /api/op  { code, ops: [ ... ] }  -> { ok: true }
 *
 * Ops are tiny and atomic:
 *   { t:"score", id:"im1", who:"a", v:9 }   v:null clears it
 *   { t:"watch", id:"im1", v:true }
 *   { t:"name",  who:"a", v:"Chris" }
 *   { t:"reset" }
 */

const kv = require("./_kv.js");
const room = require("./_room.js");

const MAX_OPS = 400; // enough to seed or reset a whole board in one call

function readBody(req) {
  if (!req.body) return {};
  if (typeof req.body === "string") {
    try { return JSON.parse(req.body); } catch { return {}; }
  }
  return req.body;
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "method_not_allowed" });
  }
  if (!kv.configured()) {
    return res.status(503).json({ error: "storage_not_configured" });
  }

  try {
    const body = readBody(req);
    const code = room.normaliseCode(body.code);
    if (!code) return res.status(400).json({ error: "bad_code" });

    const ops = Array.isArray(body.ops) ? body.ops : [];
    if (!ops.length) return res.status(400).json({ error: "no_ops" });
    if (ops.length > MAX_OPS) return res.status(413).json({ error: "too_many_ops" });

    // refuse to write into a room that was never created
    const exists = await kv.one(["HEXISTS", room.keys(code).meta, "created"]);
    if (!exists) return res.status(404).json({ error: "no_such_room" });

    const commands = [];
    for (const op of ops) {
      const cmds = room.commandsFor(code, op);
      if (!cmds) return res.status(400).json({ error: "bad_op", op });
      commands.push(...cmds);
    }
    commands.push(...kv.touch(Object.values(room.keys(code))));

    await kv.pipeline(commands);
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("op handler failed:", err);
    return res.status(500).json({ error: "server_error", message: String(err.message || err) });
  }
};
