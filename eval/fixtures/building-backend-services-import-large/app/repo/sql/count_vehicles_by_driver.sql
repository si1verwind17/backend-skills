SELECT count(*) AS vehicle_count
FROM vehicle
WHERE driver_id = %(driver_id)s
  AND deleted_at IS NULL;
