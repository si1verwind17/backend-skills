-- UC5: mobile app lists a driver's reservations across all states.
SELECT
    reservation_id, public_id, garage_id, spot_id, driver_id, status,
    window_start, window_end, checked_in_at, completed_at, cancelled_at,
    created_at, updated_at
FROM reservation
WHERE driver_id = %(driver_id)s
ORDER BY window_start DESC;
