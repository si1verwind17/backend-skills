SELECT driver_id, display_name, email, phone, notify_reminders, created_at, updated_at
FROM driver
WHERE driver_id = %(driver_id)s;
