SELECT public_id, garage_code, spot_label, driver_id, start_at, end_at, status,
       checked_in_at, checked_out_at, cancelled_at
FROM reservation_detail
WHERE reservation_id = %(reservation_id)s
