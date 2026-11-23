-- Postgres dialect (LD3). Timestamps are timestamptz; the application supplies every
-- business timestamp from its injected clock, so only created_at defaults to now().

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE reservation_status AS ENUM ('booked', 'checked_in', 'completed', 'cancelled');
CREATE TYPE outbox_event_type AS ENUM ('reserved', 'checked_in', 'completed', 'cancelled');
CREATE TYPE outbox_status AS ENUM ('pending', 'published', 'parked');

CREATE TABLE garage (
    garage_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       text        NOT NULL,
    timezone   text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL
);

CREATE TABLE spot (
    spot_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    garage_id  bigint      NOT NULL REFERENCES garage (garage_id),
    label      text        NOT NULL,
    active     boolean     NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL,
    UNIQUE (garage_id, label),
    UNIQUE (spot_id, garage_id)
);

CREATE TABLE reservation (
    reservation_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id       uuid               NOT NULL UNIQUE,
    garage_id       bigint             NOT NULL,
    spot_id         bigint             NOT NULL,
    driver_id       text               NOT NULL,
    idempotency_key text               NOT NULL CHECK (char_length(idempotency_key) BETWEEN 1 AND 128),
    window_start    timestamptz        NOT NULL,
    window_end      timestamptz        NOT NULL,
    status          reservation_status NOT NULL,
    checked_in_at   timestamptz,
    checked_out_at  timestamptz,
    cancelled_at    timestamptz,
    created_at      timestamptz        NOT NULL DEFAULT now(),
    updated_at      timestamptz        NOT NULL,
    FOREIGN KEY (spot_id, garage_id) REFERENCES spot (spot_id, garage_id),
    UNIQUE (driver_id, idempotency_key),
    CONSTRAINT reservation_window_ordered CHECK (window_end > window_start),
    CONSTRAINT reservation_checked_in_stamp CHECK (
        (status IN ('checked_in', 'completed')) = (checked_in_at IS NOT NULL)),
    CONSTRAINT reservation_checked_out_stamp CHECK (
        (status = 'completed') = (checked_out_at IS NOT NULL)),
    CONSTRAINT reservation_cancelled_stamp CHECK (
        (status = 'cancelled') = (cancelled_at IS NOT NULL)),
    -- R1: a spot is never double-booked. Windows are half-open (R19, R20); only booked and
    -- checked_in reservations hold the spot (R4).
    CONSTRAINT reservation_no_double_booking EXCLUDE USING gist (
        spot_id WITH =,
        tstzrange(window_start, window_end, '[)') WITH &&
    ) WHERE (status IN ('booked', 'checked_in'))
);

CREATE TABLE outbox (
    outbox_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id       uuid              NOT NULL UNIQUE,
    reservation_id bigint            NOT NULL REFERENCES reservation (reservation_id),
    event_type     outbox_event_type NOT NULL,
    payload        jsonb             NOT NULL,
    status         outbox_status     NOT NULL DEFAULT 'pending',
    attempts       integer           NOT NULL DEFAULT 0,
    next_attempt_at timestamptz      NOT NULL,
    last_error     text,
    published_at   timestamptz,
    created_at     timestamptz       NOT NULL DEFAULT now(),
    updated_at     timestamptz       NOT NULL,
    UNIQUE (reservation_id, event_type),
    CONSTRAINT outbox_published_stamp CHECK ((status = 'published') = (published_at IS NOT NULL))
);
