-- UC6: garage staff lookup by garage and (already timezone-converted) UTC
-- window. Overlap semantics, not exact containment: a reservation
-- spanning midnight is returned for both days it touches.
SELECT
    reservation_id, public_id, garage_id, spot_id, driver_id, status,
    window_start, window_end, checked_in_at, completed_at, cancelled_at,
    created_at, updated_at
FROM reservation
WHERE garage_id = %(garage_id)s
  AND window_start < %(range_end)s
  AND window_end > %(range_start)s
ORDER BY window_start;
