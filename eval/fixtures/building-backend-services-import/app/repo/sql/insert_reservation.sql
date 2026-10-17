-- UC1: create a reservation in 'reserved' state for a specific candidate
-- spot. Relies on excl_reservation_spot_active_window (see ddl) to reject
-- an overlapping double-booking race-safely; the caller catches that
-- specific integrity error and retries with the next candidate spot.
INSERT INTO reservation (public_id, garage_id, spot_id, driver_id, window_start, window_end)
VALUES (%(public_id)s, %(garage_id)s, %(spot_id)s, %(driver_id)s, %(window_start)s, %(window_end)s)
RETURNING
    reservation_id, public_id, garage_id, spot_id, driver_id, status,
    window_start, window_end, checked_in_at, completed_at, cancelled_at,
    created_at, updated_at;
