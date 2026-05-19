import "server-only";

import { Pool } from "pg";

// One shared pool per server process. In Next dev the module is
// re-evaluated on hot reload, so stash it on globalThis to avoid leaking
// pools. Connection params come from the same POSTGRES_* env the rest of
// the stack uses (see .env.example). Nothing here is ever sent to the
// browser — BFF route handlers query and return only shaped JSON.
declare global {
  // eslint-disable-next-line no-var
  var __noetherPgPool: Pool | undefined;
}

function makePool(): Pool {
  return new Pool({
    host: process.env.POSTGRES_HOST ?? "timescaledb",
    port: Number(process.env.POSTGRES_PORT ?? 5432),
    database: process.env.POSTGRES_DB ?? "noether",
    user: process.env.POSTGRES_USER ?? "noether",
    password: process.env.POSTGRES_PASSWORD ?? "",
    max: 5,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
  });
}

export const pool: Pool = globalThis.__noetherPgPool ?? makePool();
if (process.env.NODE_ENV !== "production") {
  globalThis.__noetherPgPool = pool;
}
