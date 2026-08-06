/**
 * Room storage shape. Everything lives in three Redis hashes per room:
 *
 *   room:<code>:meta     a -> name, b -> name, created -> iso date
 *   room:<code>:scores   "<titleId>.<a|b>" -> "1".."10"
 *   room:<code>:watched  "<titleId>" -> "1"
 *
 * Splitting scores to one field per person per title means every edit is a
 * single atomic HSET/HDEL. Two people scoring at the same moment can never
 * clobber each other, so there is no revision counter or merge step.
 */

const kv = require("./_kv.js");

// no 0/O/1/I/L, so a code is safe to read aloud or retype
const ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const CODE_LEN = 8;

function newCode() {
  const bytes = require("crypto").randomBytes(CODE_LEN);
  let out = "";
  for (let i = 0; i < CODE_LEN; i++) {
    out += ALPHABET[bytes[i] % ALPHABET.length];
    if (i === 3) out += "-";
  }
  return out;
}

/** Accepts "ab12cd34" or "AB12-CD34" and normalises to "AB12-CD34". */
function normaliseCode(raw) {
  if (typeof raw !== "string") return null;
  const bare = raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (bare.length !== CODE_LEN) return null;
  for (const ch of bare) if (!ALPHABET.includes(ch)) return null;
  return bare.slice(0, 4) + "-" + bare.slice(4);
}

const keys = (code) => ({
  meta: `room:${code}:meta`,
  scores: `room:${code}:scores`,
  watched: `room:${code}:watched`,
});

const TITLE_ID = /^[a-z0-9]{1,12}$/;
const clampName = (v) => String(v == null ? "" : v).slice(0, 12);

async function load(code) {
  const k = keys(code);
  const [meta, scores, watched] = await kv.pipeline([
    ["HGETALL", k.meta],
    ["HGETALL", k.scores],
    ["HGETALL", k.watched],
  ]);

  const metaObj = kv.pairsToObject(meta);
  if (!metaObj.created) return null; // no such room

  const scoreObj = kv.pairsToObject(scores);
  const out = { names: { a: metaObj.a || "Me", b: metaObj.b || "Her" }, scores: {}, watched: {} };

  for (const [field, value] of Object.entries(scoreObj)) {
    const dot = field.lastIndexOf(".");
    if (dot < 0) continue;
    const id = field.slice(0, dot);
    const who = field.slice(dot + 1);
    if (who !== "a" && who !== "b") continue;
    const n = Number(value);
    if (!Number.isInteger(n) || n < 1 || n > 10) continue;
    (out.scores[id] = out.scores[id] || {})[who] = n;
  }
  for (const id of Object.keys(kv.pairsToObject(watched))) out.watched[id] = true;

  return out;
}

/** Build the commands for one op, or null if the op is malformed. */
function commandsFor(code, op) {
  const k = keys(code);
  if (!op || typeof op !== "object") return null;

  if (op.t === "score") {
    if (!TITLE_ID.test(String(op.id))) return null;
    if (op.who !== "a" && op.who !== "b") return null;
    const field = `${op.id}.${op.who}`;
    if (op.v === null) return [["HDEL", k.scores, field]];
    const n = Number(op.v);
    if (!Number.isInteger(n) || n < 1 || n > 10) return null;
    // scoring something implies you watched it
    return [
      ["HSET", k.scores, field, String(n)],
      ["HSET", k.watched, String(op.id), "1"],
    ];
  }

  if (op.t === "watch") {
    if (!TITLE_ID.test(String(op.id))) return null;
    return op.v
      ? [["HSET", k.watched, String(op.id), "1"]]
      : [["HDEL", k.watched, String(op.id)]];
  }

  if (op.t === "name") {
    if (op.who !== "a" && op.who !== "b") return null;
    return [["HSET", k.meta, op.who, clampName(op.v)]];
  }

  if (op.t === "reset") {
    return [["DEL", k.scores], ["DEL", k.watched]];
  }

  return null;
}

/** Seed a brand new room from a client's existing local state. */
function seedCommands(code, state) {
  const k = keys(code);
  const cmds = [
    ["HSET", k.meta, "a", clampName(state?.names?.a || "Me"),
      "b", clampName(state?.names?.b || "Her"),
      "created", new Date().toISOString()],
  ];

  const scoreArgs = [];
  const scores = state && typeof state.scores === "object" ? state.scores : {};
  for (const [id, pair] of Object.entries(scores).slice(0, 500)) {
    if (!TITLE_ID.test(id) || !pair || typeof pair !== "object") continue;
    for (const who of ["a", "b"]) {
      const n = Number(pair[who]);
      if (Number.isInteger(n) && n >= 1 && n <= 10) scoreArgs.push(`${id}.${who}`, String(n));
    }
  }
  if (scoreArgs.length) cmds.push(["HSET", k.scores, ...scoreArgs]);

  const watchedArgs = [];
  const watched = state && typeof state.watched === "object" ? state.watched : {};
  for (const id of Object.keys(watched).slice(0, 500)) {
    if (TITLE_ID.test(id) && watched[id]) watchedArgs.push(id, "1");
  }
  if (watchedArgs.length) cmds.push(["HSET", k.watched, ...watchedArgs]);

  return cmds.concat(kv.touch([k.meta, k.scores, k.watched]));
}

module.exports = { newCode, normaliseCode, keys, load, commandsFor, seedCommands };
