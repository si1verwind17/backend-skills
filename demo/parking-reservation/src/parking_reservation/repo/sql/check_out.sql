WITH upd AS (
    UPDATE reservation
    -- The stamp is never earlier than the check-in, whatever clock skew separates instances.
    SET status = 'completed',
        checked_out_at = GREATEST(%(now)s, checked_in_at),
        updated_at = GREATEST(%(now)s, checked_in_at)
    WHERE public_id = %(public_id)s
      AND driver_id = %(driver_id)s
      AND status = 'checked_in'
    RETURNING *
), ob AS (
    INSERT INTO outbox (event_id, reservation_id, event_type, payload, next_attempt_at, updated_at)
    SELECT %(event_id)s, upd.reservation_id, 'completed'::outbox_event_type,
           outbox_payload(%(event_id)s, 'completed', upd.updated_at, to_jsonb(upd)),
           %(now)s, %(now)s
    FROM upd
)
SELECT public_id, garage_id, spot_id, driver_id, window_start, window_end, status,
       checked_in_at, checked_out_at, cancelled_at
FROM upd
