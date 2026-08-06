/**
 * Tiny Redis client over the Upstash REST API.
 *
 * No npm dependencies: Node 18+ has global fetch, so this works on Vercel with
 * nothing installed. Reads whichever env var pair is present, since Vercel's
 * own KV integration and a direct Upstash integration name them differently.
 */

const BASE =
  process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "";
const TOKEN =
  process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";

/** Rooms stick around for well over a year, refreshed on every write. */
const TTL_SECONDS = 400 * 24 * 60 * 60;

function configured() {
  return Boolean(BASE && TOKEN);
}

async function call(path, body) {
  const res = await fetch(BASE.replace(/\/$/, "") + path, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`redis ${res.status}: ${text.slice(0, 200)}`);
  return JSON.parse(text);
}

/** Run several commands in one round trip. Returns an array of results. */
async function pipeline(commands) {
  if (!commands.length) return [];
  const out = await call("/pipeline", commands);
  return out.map((entry) => {
    if (entry && entry.error) throw new Error(`redis: ${entry.error}`);
    return entry ? entry.result : null;
  });
}

async function one(command) {
  const [result] = await pipeline([command]);
  return result;
}

/** HGETALL comes back as a flat [field, value, field, value, ...] array. */
function pairsToObject(flat) {
  const obj = {};
  if (!Array.isArray(flat)) return obj;
  for (let i = 0; i < flat.length; i += 2) obj[flat[i]] = flat[i + 1];
  return obj;
}

function touch(keys) {
  return keys.map((k) => ["EXPIRE", k, TTL_SECONDS]);
}

module.exports = {
  configured,
  pipeline,
  one,
  pairsToObject,
  touch,
  TTL_SECONDS,
};
