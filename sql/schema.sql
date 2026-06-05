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
