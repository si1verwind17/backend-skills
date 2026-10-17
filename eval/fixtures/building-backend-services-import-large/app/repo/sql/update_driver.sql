-- The service merges the patch onto the current row first, so every
-- column is written as given (this is how an email can be cleared when a
-- phone number remains).
UPDATE driver
SET display_name = %(display_name)s,
    email = %(email)s,
    phone = %(phone)s,
    notify_reminders = %(notify_reminders)s,
    updated_at = %(now)s
WHERE driver_id = %(driver_id)s
RETURNING driver_id, display_name, email, phone, notify_reminders, created_at, updated_at;
