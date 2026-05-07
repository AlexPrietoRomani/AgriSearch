/**
 * Active Learning Worker configuration.
 *
 * The Rust microservice runs on port 3001 by default.
 * Override via PUBLIC_AL_WORKER_URL env var at build time.
 */
export const AL_WORKER_URL =
  (typeof import.meta !== "undefined" && import.meta.env?.PUBLIC_AL_WORKER_URL) ||
  "http://localhost:3001";
