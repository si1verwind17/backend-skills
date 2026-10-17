-- Reservations still holding the spot: not yet ended and not finished.
SELECT count(*) AS open_count
FROM reservation
WHERE spot_id = %(spot_id)s
  AND status IN ('reserved', 'checked_in')
  AND window_end > %(now)s;
