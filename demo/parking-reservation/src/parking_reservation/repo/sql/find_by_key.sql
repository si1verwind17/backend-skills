SELECT public_id, garage_id, spot_id, driver_id, window_start, window_end, status,
       checked_in_at, checked_out_at, cancelled_at
FROM reservation
WHERE driver_id = %(driver_id)s AND idempotency_key = %(idempotency_key)s
