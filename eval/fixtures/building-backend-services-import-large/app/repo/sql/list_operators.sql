SELECT operator_id, name, contact_email, created_at, updated_at
FROM operator
ORDER BY name
LIMIT %(limit)s OFFSET %(offset)s;
