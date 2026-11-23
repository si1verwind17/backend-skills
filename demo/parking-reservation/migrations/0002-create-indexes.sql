-- AP3: staff day lookup, overlap of a garage's reservations with a date range.
CREATE INDEX reservation_garage_window_idx ON reservation
    USING gist (garage_id, tstzrange(window_start, window_end, '[)'));

-- AP6: the relay scans due pending outbox rows.
CREATE INDEX outbox_pending_idx ON outbox (next_attempt_at, outbox_id) WHERE status = 'pending';

-- Ops path: all outbox rows of one reservation. A driver's reservations are served by the
-- leading column of the unique (driver_id, idempotency_key) index.
CREATE INDEX outbox_reservation_idx ON outbox (reservation_id);
