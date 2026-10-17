INSERT INTO garage (operator_id, name, address, timezone, created_at, updated_at)
VALUES (%(operator_id)s, %(name)s, %(address)s, %(timezone)s, %(now)s, %(now)s)
RETURNING garage_id, operator_id, name, address, timezone, is_active, created_at, updated_at;
