-- A1 staff lookup: garage + overlapping range.
CREATE INDEX reservation_garage_during_idx ON reservation
    USING gist (garage_id, tstzrange(start_at, end_at, '[)'));
-- A5 relay scan: pending events in id order (uuidv7 is time-ordered).
CREATE INDEX outbox_event_pending_idx ON outbox_event (event_id) WHERE status = 'pending';
-- Ops/debug: events of one reservation; FK support.
CREATE INDEX outbox_event_reservation_idx ON outbox_event (reservation_id);
-- Ops/debug: a driver's reservations.
CREATE INDEX reservation_driver_idx ON reservation (driver_id, start_at);
