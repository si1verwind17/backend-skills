-- Physical model for data-design.md (PostgreSQL dialect). Extension btree_gist is required.
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE reservation_status AS ENUM ('reserved', 'checked_in', 'completed', 'cancelled');
CREATE TYPE outbox_status AS ENUM ('pending', 'published', 'parked');

CREATE TABLE garage (
    garage_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        text NOT NULL UNIQUE,
    name        text NOT NULL,
    time_zone   text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL
);

CREATE TABLE spot (
    spot_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    garage_id   bigint NOT NULL REFERENCES garage (garage_id),
    label       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL,
    UNIQUE (garage_id, label),
    UNIQUE (spot_id, garage_id)
);

CREATE TABLE reservation (
    reservation_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id        uuid NOT NULL UNIQUE,
    garage_id        bigint NOT NULL REFERENCES garage (garage_id),
    spot_id          bigint NOT NULL,
    driver_id        text NOT NULL,
    idempotency_key  text NOT NULL,
    start_at         timestamptz NOT NULL,
    end_at           timestamptz NOT NULL,
    status           reservation_status NOT NULL DEFAULT 'reserved',
    checked_in_at    timestamptz,
    checked_out_at   timestamptz,
    cancelled_at     timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL,
    FOREIGN KEY (spot_id, garage_id) REFERENCES spot (spot_id, garage_id),
    UNIQUE (driver_id, idempotency_key),
    CONSTRAINT reservation_window_ordered CHECK (end_at > start_at),
    CONSTRAINT reservation_checked_in_stamp CHECK ((checked_in_at IS NOT NULL) = (status IN ('checked_in', 'completed'))),
    CONSTRAINT reservation_checked_out_stamp CHECK ((checked_out_at IS NOT NULL) = (status = 'completed')),
    CONSTRAINT reservation_cancelled_stamp CHECK ((cancelled_at IS NOT NULL) = (status = 'cancelled')),
    -- R1, R2, R3, R17, R19, R20: no two non-cancelled reservations of a spot overlap; windows are half-open.
    CONSTRAINT reservation_no_double_booking EXCLUDE USING gist (
        spot_id WITH =,
        tstzrange(start_at, end_at, '[)') WITH &&
    ) WHERE (status <> 'cancelled')
);

CREATE TABLE outbox_event (
    event_id      uuid PRIMARY KEY,
    topic         text NOT NULL,
    reservation_id bigint NOT NULL REFERENCES reservation (reservation_id),
    payload       jsonb NOT NULL,
    status        outbox_status NOT NULL DEFAULT 'pending',
    attempts      integer NOT NULL DEFAULT 0,
    last_error    text,
    published_at  timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL,
    CONSTRAINT outbox_published_stamp CHECK ((published_at IS NOT NULL) = (status = 'published'))
);

CREATE TABLE schema_migration (
    version     text PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now()
);
