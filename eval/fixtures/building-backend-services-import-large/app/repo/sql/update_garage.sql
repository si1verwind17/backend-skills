-- Partial update: NULL parameters leave the column unchanged.
UPDATE garage
SET name = COALESCE(%(name)s, name),
    address = COALESCE(%(address)s, address),
    timezone = COALESCE(%(timezone)s, timezone),
    is_active = COALESCE(%(is_active)s, is_active),
    updated_at = %(now)s
WHERE garage_id = %(garage_id)s
RETURNING garage_id, operator_id, name, address, timezone, is_active, created_at, updated_at;
