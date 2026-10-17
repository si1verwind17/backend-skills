-- UC1: candidate spots in a garage with no overlapping active reservation
-- for the requested window. Ordered for determinism; the caller tries each
-- in turn and falls back to the next on an exclusion-constraint conflict
-- (see data-design.md write-path #1 and reservation_repo.create_reservation).
SELECT s.spot_id
FROM spot s
WHERE s.garage_id = %(garage_id)s
  AND s.is_active
  AND NOT EXISTS (
      SELECT 1
      FROM reservation r
      WHERE r.spot_id = s.spot_id
        AND r.status IN ('reserved', 'checked_in')
        AND tstzrange(r.window_start, r.window_end) && tstzrange(%(window_start)s, %(window_end)s)
  )
ORDER BY s.spot_id
LIMIT %(limit)s;
