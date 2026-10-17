-- Soft delete, so past reservations and reports can still name the plate.
-- Returns whether the vehicle was the default, so the caller knows to
-- promote another one.
WITH target AS (
    SELECT vehicle_id, is_default
    FROM vehicle
    WHERE vehicle_id = %(vehicle_id)s
      AND driver_id = %(driver_id)s
      AND deleted_at IS NULL
    FOR UPDATE
)
UPDATE vehicle v
SET deleted_at = %(now)s, is_default = false
FROM target t
WHERE v.vehicle_id = t.vehicle_id
RETURNING v.vehicle_id, t.is_default AS was_default;
