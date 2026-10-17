UPDATE vehicle
SET is_default = false
WHERE driver_id = %(driver_id)s
  AND is_default
  AND deleted_at IS NULL;
