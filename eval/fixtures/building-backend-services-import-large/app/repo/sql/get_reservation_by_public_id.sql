SELECT
    reservation_id, public_id, garage_id, spot_id, driver_id, status,
    window_start, window_end, checked_in_at, completed_at, cancelled_at,
    created_at, updated_at
FROM reservation
WHERE public_id = %(public_id)s;
