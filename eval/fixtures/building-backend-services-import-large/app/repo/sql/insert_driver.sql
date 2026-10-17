INSERT INTO driver (driver_id, display_name, email, phone, notify_reminders, created_at, updated_at)
VALUES (%(driver_id)s, %(display_name)s, %(email)s, %(phone)s, %(notify_reminders)s, %(now)s, %(now)s)
RETURNING driver_id, display_name, email, phone, notify_reminders, created_at, updated_at;
