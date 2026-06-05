-- ─────────────────────────────────────────────────────────────────────────────
-- Row Level Security (RLS) posture for this assignment:
--
-- RLS is INTENTIONALLY LEFT DISABLED on all three tables below. Supabase tables
-- have RLS disabled by default, so no policies are required for this project.
--
-- Key separation is still enforced at the application layer:
--   • ETL (GitHub Actions) writes using SUPABASE_SERVICE_ROLE_KEY.
--   • Dashboard (Streamlit) reads using SUPABASE_ANON_KEY (SELECT only).
--
-- IF you choose to ENABLE RLS later, you MUST add a read policy for the anon
-- role on each table, or the dashboard's anon-key reads will return zero rows:
--
--   ALTER TABLE prices     ENABLE ROW LEVEL SECURITY;
--   CREATE POLICY anon_read_prices     ON prices     FOR SELECT TO anon USING (true);
--   ALTER TABLE fear_greed ENABLE ROW LEVEL SECURITY;
--   CREATE POLICY anon_read_fear_greed ON fear_greed FOR SELECT TO anon USING (true);
--   ALTER TABLE onchain    ENABLE ROW LEVEL SECURITY;
--   CREATE POLICY anon_read_onchain    ON onchain    FOR SELECT TO anon USING (true);
--
-- Writes remain service-role-only because the service role bypasses RLS.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS prices (
  id          SERIAL PRIMARY KEY,
  coin_id     TEXT        NOT NULL,
  symbol      TEXT        NOT NULL,
  rank        INTEGER,
  price_usd   NUMERIC     NOT NULL,
  market_cap  NUMERIC,
  volume_24h  NUMERIC,
  change_24h  NUMERIC,
  change_7d   NUMERIC,
  bucket_time TIMESTAMPTZ NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (coin_id, bucket_time)
);

CREATE TABLE IF NOT EXISTS fear_greed (
  id          SERIAL PRIMARY KEY,
  value       INTEGER     NOT NULL,
  label       TEXT        NOT NULL,
  recorded_at DATE        NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (recorded_at)
);

CREATE TABLE IF NOT EXISTS onchain (
  id          SERIAL PRIMARY KEY,
  metric      TEXT        NOT NULL,
  value       NUMERIC     NOT NULL,
  recorded_at DATE        NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (metric, recorded_at)
);
