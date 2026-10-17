-- Reservation counts by status for reservations whose window starts on a
-- garage-local date inside the range.
SELECT r.status, count(*) AS count
FROM reservation r
JOIN garage g ON g.garage_id = r.garage_id
WHERE r.garage_id = %(garage_id)s
  AND (r.window_start AT TIME ZONE g.timezone)::date BETWEEN %(first)s AND %(last)s
GROUP BY r.status
ORDER BY r.status;
