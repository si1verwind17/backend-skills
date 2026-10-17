SELECT garage_id, operator_id, name, address, timezone, is_active, created_at, updated_at
FROM garage
WHERE operator_id = %(operator_id)s
  AND (%(include_inactive)s OR is_active)
ORDER BY name, garage_id;
