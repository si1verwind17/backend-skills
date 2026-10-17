INSERT INTO operator (name, contact_email, created_at, updated_at)
VALUES (%(name)s, %(contact_email)s, %(now)s, %(now)s)
RETURNING operator_id, name, contact_email, created_at, updated_at;
