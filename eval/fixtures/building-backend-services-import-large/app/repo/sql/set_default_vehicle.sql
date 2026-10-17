UPDATE vehicle
SET is_default = true
WHERE vehicle_id = %(vehicle_id)s
  AND driver_id = %(driver_id)s
  AND deleted_at IS NULL
RETURNING vehicle_id, driver_id, country_code, plate, nickname, is_default, created_at;
