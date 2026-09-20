// Offline Ed25519 signature verification in the browser via WebCrypto.
//
// Confirms a delegation hop was signed by the delegating agent WITHOUT
// trusting the server: the client rebuilds the exact canonical payload,
// imports the agent's raw public key, and verifies the signature locally.
//
// Canonicalization MUST match the backend (app/core/agent_signing.py):
// json.dumps(sort_keys=True, separators=(",",":")). For our flat payloads
// that's: sort top-level keys, compact JSON, UTF-8 bytes.

export type VerifyResult =
  | { status: "verified" }
  | { status: "failed" }
  | { status: "unsupported" }   // browser lacks Ed25519 in WebCrypto
  | { status: "no_signature" }
  | { status: "error"; message: string };

function canonicalBytes(payload: Record<string, unknown>): Uint8Array {
  const keys = Object.keys(payload).sort();
  const parts = keys.map((k) => JSON.stringify(k) + ":" + JSON.stringify(payload[k]));
  const canonical = "{" + parts.join(",") + "}";
  return new TextEncoder().encode(canonical);
}

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// Return a fresh ArrayBuffer-backed view so TS sees BufferSource with a
// concrete ArrayBuffer (not ArrayBufferLike, which TS5 rejects for
// crypto.subtle).
function toBuf(bytes: Uint8Array): ArrayBuffer {
  const buf = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buf).set(bytes);
  return buf;
}

export async function verifyHopSignature(
  signedPayload: Record<string, unknown> | null,
  signatureB64: string | null,
  publicKeyB64: string | null
): Promise<VerifyResult> {
  if (!signatureB64 || !publicKeyB64 || !signedPayload) {
    return { status: "no_signature" };
  }
  if (!globalThis.crypto?.subtle) {
    return { status: "unsupported" };
  }
  try {
    const pubBytes = b64ToBytes(publicKeyB64);
    const sigBytes = b64ToBytes(signatureB64);
    const msgBytes = canonicalBytes(signedPayload);

    let key: CryptoKey;
    try {
      // Ed25519 raw public key import; throws if the browser doesn't
      // support the algorithm.
      key = await crypto.subtle.importKey(
        "raw",
        toBuf(pubBytes),
        { name: "Ed25519" },
        false,
        ["verify"]
      );
    } catch {
      return { status: "unsupported" };
    }

    const ok = await crypto.subtle.verify(
      { name: "Ed25519" },
      key,
      toBuf(sigBytes),
      toBuf(msgBytes)
    );
    return { status: ok ? "verified" : "failed" };
  } catch (e) {
    return { status: "error", message: e instanceof Error ? e.message : String(e) };
  }
}
