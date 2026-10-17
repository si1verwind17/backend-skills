-- Occupied minutes per garage-local date: for every reservation that
-- holds a spot (cancelled ones do not), the part of its window that falls
-- inside that local day. Only dates with at least one reservation come
-- back; the service fills in the empty ones.
WITH days AS (
    SELECT
        d::date AS local_date,
        d AT TIME ZONE %(timezone)s AS day_start,
        (d + interval '1 day') AT TIME ZONE %(timezone)s AS day_end
    FROM generate_series(%(first)s::timestamp, %(last)s::timestamp, interval '1 day') AS d
)
SELECT
    days.local_date,
    count(r.reservation_id) AS reservations,
    coalesce(
        sum(ceil(extract(epoch FROM least(r.window_end, days.day_end) - greatest(r.window_start, days.day_start)) / 60)),
        0
    )::bigint AS occupied_minutes,
    (SELECT count(*) FROM spot s WHERE s.garage_id = %(garage_id)s AND s.is_active) AS active_spots
FROM days
JOIN reservation r
  ON r.garage_id = %(garage_id)s
 AND r.status IN ('reserved', 'checked_in', 'completed')
 AND r.window_start < days.day_end
 AND r.window_end > days.day_start
GROUP BY days.local_date
ORDER BY days.local_date;
