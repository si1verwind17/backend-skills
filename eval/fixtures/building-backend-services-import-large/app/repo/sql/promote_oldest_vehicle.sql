-- After the default vehicle is removed, the oldest remaining one takes
-- its place (no-op when the driver has none left).
UPDATE vehicle
SET is_default = true
WHERE vehicle_id = (
    SELECT vehicle_id FROM vehicle
    WHERE driver_id = %(driver_id)s AND deleted_at IS NULL
    ORDER BY created_at, vehicle_id
    LIMIT 1
);
