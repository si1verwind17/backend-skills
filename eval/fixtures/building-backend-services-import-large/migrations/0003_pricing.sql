-- Tariffs per garage, priced per started block within local-time bands,
-- plus persisted quotes and the charge settled for each completed
-- reservation.

CREATE TABLE tariff (
    tariff_id           bigserial PRIMARY KEY,
    garage_id           bigint NOT NULL REFERENCES garage (garage_id),
    name                text NOT NULL,
    currency            char(3) NOT NULL,
    block_minutes       smallint NOT NULL DEFAULT 15,
    grace_minutes       smallint NOT NULL DEFAULT 0,
    daily_cap_cents     integer,
    rounding_cents      smallint NOT NULL DEFAULT 1,
    valid_from          date NOT NULL,
    valid_to            date,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_tariff_block CHECK (block_minutes > 0 AND block_minutes <= 240),
    CONSTRAINT ck_tariff_grace CHECK (grace_minutes >= 0),
    CONSTRAINT ck_tariff_cap CHECK (daily_cap_cents IS NULL OR daily_cap_cents > 0),
    CONSTRAINT ck_tariff_rounding CHECK (rounding_cents IN (1, 5, 10, 50, 100)),
    CONSTRAINT ck_tariff_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    -- One tariff in force per garage on any given date.
    CONSTRAINT excl_tariff_garage_validity EXCLUDE USING gist (
        garage_id WITH =,
        daterange(valid_from, valid_to, '[)') WITH &&
    )
);

-- A band covers [start_minute, end_minute) of local time on the weekdays
-- in weekday_mask (bit 0 = Monday ... bit 6 = Sunday).
CREATE TABLE tariff_band (
    band_id                 bigserial PRIMARY KEY,
    tariff_id               bigint NOT NULL REFERENCES tariff (tariff_id) ON DELETE CASCADE,
    weekday_mask            smallint NOT NULL,
    start_minute            smallint NOT NULL,
    end_minute              smallint NOT NULL,
    rate_cents_per_block    integer NOT NULL,
    CONSTRAINT ck_tariff_band_mask CHECK (weekday_mask BETWEEN 1 AND 127),
    CONSTRAINT ck_tariff_band_range
        CHECK (start_minute >= 0 AND end_minute <= 1440 AND end_minute > start_minute),
    CONSTRAINT ck_tariff_band_rate CHECK (rate_cents_per_block >= 0)
);

CREATE INDEX ix_tariff_band_tariff ON tariff_band (tariff_id);

CREATE TABLE quote (
    quote_id        bigserial PRIMARY KEY,
    public_id       uuid NOT NULL UNIQUE,
    garage_id       bigint NOT NULL REFERENCES garage (garage_id),
    tariff_id       bigint NOT NULL REFERENCES tariff (tariff_id),
    window_start    timestamptz NOT NULL,
    window_end      timestamptz NOT NULL,
    amount_cents    integer NOT NULL,
    currency        char(3) NOT NULL,
    breakdown       jsonb NOT NULL,
    expires_at      timestamptz NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reservation_charge (
    charge_id       bigserial PRIMARY KEY,
    reservation_id  bigint NOT NULL REFERENCES reservation (reservation_id),
    garage_id       bigint NOT NULL REFERENCES garage (garage_id),
    tariff_id       bigint NOT NULL REFERENCES tariff (tariff_id),
    charged_from    timestamptz NOT NULL,
    charged_until   timestamptz NOT NULL,
    amount_cents    integer NOT NULL,
    currency        char(3) NOT NULL,
    settled_at      timestamptz NOT NULL,
    CONSTRAINT uq_reservation_charge_reservation UNIQUE (reservation_id)
);

CREATE INDEX ix_reservation_charge_garage_settled ON reservation_charge (garage_id, settled_at);
