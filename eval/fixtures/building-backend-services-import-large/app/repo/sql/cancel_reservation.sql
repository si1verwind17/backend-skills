-- UC4: reserved -> cancelled. Guarded update (R3: no cancellation once
-- checked in — the WHERE clause is the enforcement, not app logic).
UPDATE reservation
SET status = 'cancelled', cancelled_at = %(now)s, updated_at = %(now)s
WHERE public_id = %(public_id)s AND status IN ('reserved', 'checked_in')
RETURNING
    reservation_id, public_id, garage_id, spot_id, driver_id, status,
    window_start, window_end, checked_in_at, completed_at, cancelled_at,
    created_at, updated_at;
