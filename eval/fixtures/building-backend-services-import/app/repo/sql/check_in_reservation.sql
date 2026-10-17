-- UC2: reserved -> checked_in. Guarded update (R2) — zero rows returned
-- means either not found or an illegal transition; the caller disambiguates
-- with a follow-up lookup only if needed for the error message.
UPDATE reservation
SET status = 'checked_in', checked_in_at = %(now)s, updated_at = %(now)s
WHERE public_id = %(public_id)s AND status = 'reserved'
RETURNING
    reservation_id, public_id, garage_id, spot_id, driver_id, status,
    window_start, window_end, checked_in_at, completed_at, cancelled_at,
    created_at, updated_at;
