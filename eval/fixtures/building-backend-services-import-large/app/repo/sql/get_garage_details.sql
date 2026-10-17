SELECT garage_id, operator_id, name, address, timezone, is_active, created_at, updated_at
FROM garage
WHERE garage_id = %(garage_id)s;
