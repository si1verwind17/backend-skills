-- NULL parameters leave the column unchanged.
UPDATE operator
SET name = COALESCE(%(name)s, name),
    contact_email = COALESCE(%(contact_email)s, contact_email),
    updated_at = %(now)s
WHERE operator_id = %(operator_id)s
RETURNING operator_id, name, contact_email, created_at, updated_at;
