UPDATE outbox_event
SET attempts = attempts + 1,
    last_error = %(error)s,
    status = CASE WHEN attempts + 1 >= %(park_after)s THEN 'parked'::outbox_status ELSE status END,
    updated_at = %(now)s
WHERE event_id = %(event_id)s AND status = 'pending'
RETURNING status = 'parked' AS parked
