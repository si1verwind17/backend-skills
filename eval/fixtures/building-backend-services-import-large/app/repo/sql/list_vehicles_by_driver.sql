SELECT vehicle_id, driver_id, country_code, plate, nickname, is_default, created_at
FROM vehicle
WHERE driver_id = %(driver_id)s
  AND deleted_at IS NULL
ORDER BY is_default DESC, created_at, vehicle_id;
