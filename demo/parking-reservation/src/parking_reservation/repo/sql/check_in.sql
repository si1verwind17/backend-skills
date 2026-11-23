WITH upd AS (
    UPDATE reservation
    SET status = 'checked_in', checked_in_at = %(now)s, updated_at = %(now)s
    WHERE public_id = %(public_id)s
      AND driver_id = %(driver_id)s
      AND status = 'booked'
      AND %(now)s >= window_start
      AND %(now)s < window_end
    RETURNING *
), ob AS (
    INSERT INTO outbox (event_id, reservation_id, event_type, payload, next_attempt_at, updated_at)
    SELECT %(event_id)s, upd.reservation_id, 'checked_in'::outbox_event_type,
           outbox_payload(%(event_id)s, 'checked_in', %(now)s, to_jsonb(upd)),
           %(now)s, %(now)s
    FROM upd
)
SELECT public_id, garage_id, spot_id, driver_id, window_start, window_end, status,
       checked_in_at, checked_out_at, cancelled_at
FROM upd
