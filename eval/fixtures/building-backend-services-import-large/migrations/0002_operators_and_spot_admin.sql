-- Operators own garages; garages gain an address, an active flag and
-- weekly opening hours; spots gain a type, a level and an active flag.

CREATE TABLE operator (
    operator_id     bigserial PRIMARY KEY,
    name            text NOT NULL,
    contact_email   text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_operator_name UNIQUE (name)
);

ALTER TABLE garage
    ADD COLUMN operator_id bigint REFERENCES operator (operator_id),
    ADD COLUMN address     text NOT NULL DEFAULT '',
    ADD COLUMN is_active   boolean NOT NULL DEFAULT true,
    ADD COLUMN updated_at  timestamptz NOT NULL DEFAULT now();

CREATE INDEX ix_garage_operator ON garage (operator_id);

-- Minutes since local midnight, in the garage's own timezone. A weekday
-- with no row is closed all day; 0..1440 is open around the clock.
CREATE TABLE opening_hours (
    garage_id       bigint NOT NULL REFERENCES garage (garage_id) ON DELETE CASCADE,
    weekday         smallint NOT NULL,
    open_minute     smallint NOT NULL,
    close_minute    smallint NOT NULL,
    PRIMARY KEY (garage_id, weekday),
    CONSTRAINT ck_opening_hours_weekday CHECK (weekday BETWEEN 0 AND 6),
    CONSTRAINT ck_opening_hours_range
        CHECK (open_minute >= 0 AND close_minute <= 1440 AND close_minute > open_minute)
);

CREATE TABLE spot_type (
    spot_type_id    smallserial PRIMARY KEY,
    code            text NOT NULL UNIQUE,
    description     text NOT NULL
);

INSERT INTO spot_type (code, description) VALUES
    ('standard', 'Standard car space'),
    ('compact', 'Compact car space'),
    ('ev', 'Space with an electric vehicle charger'),
    ('accessible', 'Accessible space, permit required'),
    ('motorcycle', 'Motorcycle bay');

ALTER TABLE spot
    ADD COLUMN spot_type_id smallint REFERENCES spot_type (spot_type_id),
    ADD COLUMN level        text NOT NULL DEFAULT '',
    ADD COLUMN is_active    boolean NOT NULL DEFAULT true,
    ADD COLUMN updated_at   timestamptz NOT NULL DEFAULT now();

UPDATE spot SET spot_type_id = (SELECT spot_type_id FROM spot_type WHERE code = 'standard');

ALTER TABLE spot
    ALTER COLUMN spot_type_id SET DEFAULT 1,
    ALTER COLUMN spot_type_id SET NOT NULL;
