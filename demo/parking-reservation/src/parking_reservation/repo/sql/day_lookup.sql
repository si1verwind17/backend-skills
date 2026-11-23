-- One row per reservation overlapping the garage-local calendar day [day, day + 1 day).
-- A garage with no reservation yields one row whose reservation columns are null;
-- an unknown garage yields no row.
SELECT g.garage_id AS present_garage_id,
       r.public_id, r.garage_id, r.spot_id, r.driver_id, r.window_start, r.window_end, r.status,
       r.checked_in_at, r.checked_out_at, r.cancelled_at
FROM garage g
LEFT JOIN reservation r
       ON r.garage_id = g.garage_id
      AND tstzrange(r.window_start, r.window_end, '[)') && tstzrange(
              (%(day)s::date)::timestamp AT TIME ZONE g.timezone,
              ((%(day)s::date + 1)::timestamp) AT TIME ZONE g.timezone,
              '[)')
WHERE g.garage_id = %(garage_id)s
ORDER BY r.window_start, r.spot_id, r.public_id
