SELECT public_id, garage_code, spot_label, driver_id, start_at, end_at, status,
       checked_in_at, checked_out_at, cancelled_at
FROM reservation_detail
WHERE driver_id = %(driver_id)s AND idempotency_key = %(idempotency_key)s
