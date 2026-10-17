-- Initial schema: garages, their spots, reservations, and the billing
-- outbox that hands completed reservations to billing.

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE garage (
    garage_id   bigserial PRIMARY KEY,
    name        text NOT NULL,
    timezone    text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE spot (
    spot_id     bigserial PRIMARY KEY,
    garage_id   bigint NOT NULL REFERENCES garage (garage_id),
    code        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_spot_garage_code UNIQUE (garage_id, code)
);

CREATE TABLE reservation (
    reservation_id  bigserial PRIMARY KEY,
    public_id       uuid NOT NULL UNIQUE,
    garage_id       bigint NOT NULL REFERENCES garage (garage_id),
    spot_id         bigint NOT NULL REFERENCES spot (spot_id),
    driver_id       bigint NOT NULL,
    status          text NOT NULL DEFAULT 'reserved',
    window_start    timestamptz NOT NULL,
    window_end      timestamptz NOT NULL,
    checked_in_at   timestamptz,
    completed_at    timestamptz,
    cancelled_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_reservation_status
        CHECK (status IN ('reserved', 'checked_in', 'completed', 'cancelled')),
    CONSTRAINT ck_reservation_window CHECK (window_end > window_start),
    CONSTRAINT excl_reservation_spot_active_window EXCLUDE USING gist (
        spot_id WITH =,
        tstzrange(window_start, window_end) WITH &&
    ) WHERE (status IN ('reserved', 'checked_in'))
);

CREATE INDEX ix_reservation_driver ON reservation (driver_id, window_start DESC);
CREATE INDEX ix_reservation_garage_window ON reservation (garage_id, window_start);

CREATE TABLE billing_outbox (
    outbox_id               bigserial PRIMARY KEY,
    reservation_id          bigint NOT NULL REFERENCES reservation (reservation_id),
    reservation_public_id   uuid NOT NULL,
    driver_id               bigint NOT NULL,
    garage_id               bigint NOT NULL,
    spot_id                 bigint NOT NULL,
    window_start            timestamptz NOT NULL,
    window_end              timestamptz NOT NULL,
    completed_at            timestamptz NOT NULL,
    published_at            timestamptz,
    attempt_count           integer NOT NULL DEFAULT 0,
    last_error              text,
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_billing_outbox_reservation UNIQUE (reservation_id)
);

CREATE INDEX ix_billing_outbox_unpublished ON billing_outbox (created_at)
    WHERE published_at IS NULL;
