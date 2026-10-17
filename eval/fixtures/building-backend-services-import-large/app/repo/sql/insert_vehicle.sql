-- A driver's first saved vehicle becomes the default.
INSERT INTO vehicle (driver_id, country_code, plate, nickname, is_default, created_at)
VALUES (
    %(driver_id)s, %(country_code)s, %(plate)s, %(nickname)s,
    NOT EXISTS (
        SELECT 1 FROM vehicle v
        WHERE v.driver_id = %(driver_id)s AND v.deleted_at IS NULL
    ),
    %(now)s
)
RETURNING vehicle_id, driver_id, country_code, plate, nickname, is_default, created_at;
