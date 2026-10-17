-- Driver accounts and their saved vehicles. reservation.driver_id predates
-- this table and is not a foreign key: reservations made before accounts
-- existed carry ids issued by the mobile app's identity provider, which
-- driver.driver_id adopts as-is.

CREATE TABLE driver (
    driver_id           bigint PRIMARY KEY,
    display_name        text NOT NULL,
    email               text,
    phone               text,
    notify_reminders    boolean NOT NULL DEFAULT true,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_driver_contact CHECK (email IS NOT NULL OR phone IS NOT NULL)
);

CREATE UNIQUE INDEX uq_driver_email ON driver (lower(email)) WHERE email IS NOT NULL;

CREATE TABLE vehicle (
    vehicle_id      bigserial PRIMARY KEY,
    driver_id       bigint NOT NULL REFERENCES driver (driver_id),
    country_code    char(2) NOT NULL,
    plate           text NOT NULL,
    nickname        text NOT NULL DEFAULT '',
    is_default      boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    deleted_at      timestamptz
);

CREATE UNIQUE INDEX uq_vehicle_driver_plate ON vehicle (driver_id, country_code, plate)
    WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_vehicle_driver_default ON vehicle (driver_id)
    WHERE is_default AND deleted_at IS NULL;
