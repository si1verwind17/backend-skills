-- Read model joining a reservation with its garage code and spot label (used by every reservation read).
CREATE VIEW reservation_detail AS
SELECT r.reservation_id, r.public_id, r.garage_id, g.code AS garage_code, s.label AS spot_label,
       r.driver_id, r.idempotency_key, r.start_at, r.end_at, r.status,
       r.checked_in_at, r.checked_out_at, r.cancelled_at
FROM reservation r
JOIN garage g ON g.garage_id = r.garage_id
JOIN spot s ON s.spot_id = r.spot_id;

COMMENT ON VIEW reservation_detail IS 'Reservation joined with garage code and spot label; read model for the API (no data of its own).';
