-- UC3: checked_in -> completed, atomically with writing the billing outbox
-- row (data-design.md write-path #3). One statement, one round trip: if
-- the guarded UPDATE matches zero rows (illegal transition / not found),
-- the outbox INSERT's SELECT also produces zero rows, so nothing is
-- written on either side (AC3.2). ON CONFLICT DO NOTHING is an extra guard
-- against a duplicate outbox row if this statement is ever retried after a
-- partial failure (AC3.3 — at most one notification per reservation).
WITH upd AS (
    UPDATE reservation
    SET status = 'completed', completed_at = %(now)s, updated_at = %(now)s
    WHERE public_id = %(public_id)s AND status = 'checked_in'
    RETURNING
        reservation_id, public_id, garage_id, spot_id, driver_id, status,
        window_start, window_end, checked_in_at, completed_at, cancelled_at,
        created_at, updated_at
),
outbox AS (
    INSERT INTO billing_outbox (
        reservation_id, reservation_public_id, driver_id, garage_id, spot_id,
        window_start, window_end, completed_at
    )
    SELECT reservation_id, public_id, driver_id, garage_id, spot_id, window_start, window_end, completed_at
    FROM upd
    ON CONFLICT (reservation_id) DO NOTHING
    RETURNING outbox_id
)
SELECT * FROM upd;
