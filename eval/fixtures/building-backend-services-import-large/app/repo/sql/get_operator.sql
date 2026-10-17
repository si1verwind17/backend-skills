SELECT operator_id, name, contact_email, created_at, updated_at
FROM operator
WHERE operator_id = %(operator_id)s;
