WITH picked AS (
    SELECT s.spot_id
    FROM spot s
    WHERE s.garage_id = %(garage_id)s
      AND s.active
      AND NOT EXISTS (
          SELECT 1
          FROM reservation r
          WHERE r.spot_id = s.spot_id
            AND r.status IN ('booked', 'checked_in')
            AND tstzrange(r.window_start, r.window_end, '[)')
                && tstzrange(%(window_start)s, %(window_end)s, '[)')
      )
    ORDER BY s.spot_id
    LIMIT 1
), ins AS (
    INSERT INTO reservation (public_id, garage_id, spot_id, driver_id, idempotency_key,
                             window_start, window_end, status, updated_at)
    SELECT %(public_id)s, %(garage_id)s, picked.spot_id, %(driver_id)s, %(idempotency_key)s,
           %(window_start)s, %(window_end)s, 'booked'::reservation_status, %(now)s
    FROM picked
    ON CONFLICT (driver_id, idempotency_key) DO NOTHING
    RETURNING *
), ob AS (
    INSERT INTO outbox (event_id, reservation_id, event_type, payload, next_attempt_at, updated_at)
    SELECT %(event_id)s, ins.reservation_id, 'reserved'::outbox_event_type,
           outbox_payload(%(event_id)s, 'reserved', %(now)s, to_jsonb(ins)),
           %(now)s, %(now)s
    FROM ins
)
SELECT public_id, garage_id, spot_id, driver_id, window_start, window_end, status,
       checked_in_at, checked_out_at, cancelled_at
FROM ins
