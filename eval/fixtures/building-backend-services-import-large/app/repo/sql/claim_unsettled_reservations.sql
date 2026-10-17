-- Completed reservations that have not been charged yet, oldest first.
-- SKIP LOCKED lets overlapping settlement runs split the work instead of
-- pricing the same reservation twice; the unique constraint on
-- reservation_charge.reservation_id is the backstop.
SELECT
    r.reservation_id, r.garage_id, g.timezone, r.window_start, r.window_end, r.completed_at
FROM reservation r
JOIN garage g ON g.garage_id = r.garage_id
WHERE r.status = 'completed'
  AND NOT EXISTS (
      SELECT 1 FROM reservation_charge c WHERE c.reservation_id = r.reservation_id
  )
ORDER BY r.completed_at
LIMIT %(limit)s
FOR UPDATE OF r SKIP LOCKED;
