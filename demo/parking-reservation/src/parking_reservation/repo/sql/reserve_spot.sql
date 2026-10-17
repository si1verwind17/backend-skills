SELECT outcome, reservation_id
FROM reserve_spot(
    %(garage_code)s, %(driver_id)s, %(idempotency_key)s, %(start_at)s, %(end_at)s,
    %(public_id)s, %(event_id)s, %(now)s)
