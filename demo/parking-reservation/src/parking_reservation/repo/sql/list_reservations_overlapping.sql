SELECT public_id, garage_code, spot_label, driver_id, start_at, end_at, status,
       checked_in_at, checked_out_at, cancelled_at
FROM reservation_detail
WHERE garage_code = %(garage_code)s
  AND tstzrange(start_at, end_at, '[)') && tstzrange(%(range_start)s, %(range_end)s, '[)')
ORDER BY start_at, spot_label COLLATE "C", reservation_id
