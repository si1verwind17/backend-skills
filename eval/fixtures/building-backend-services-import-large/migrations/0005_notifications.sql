-- Outbox for driver notifications (reservation reminders). Rows are
-- scheduled ahead of time and dispatched once send_after has passed.

CREATE TABLE notification_outbox (
    notification_id     bigserial PRIMARY KEY,
    reservation_id      bigint NOT NULL REFERENCES reservation (reservation_id),
    driver_id           bigint NOT NULL,
    kind                text NOT NULL,
    send_after          timestamptz NOT NULL,
    published_at        timestamptz,
    skipped_at          timestamptz,
    skip_reason         text,
    attempt_count       integer NOT NULL DEFAULT 0,
    last_error          text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_notification_kind CHECK (kind IN ('reservation_reminder')),
    CONSTRAINT uq_notification_reservation_kind UNIQUE (reservation_id, kind)
);

CREATE INDEX ix_notification_outbox_due ON notification_outbox (send_after)
    WHERE published_at IS NULL AND skipped_at IS NULL;
