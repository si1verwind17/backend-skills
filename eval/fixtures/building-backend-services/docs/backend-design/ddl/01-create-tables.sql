-- Gift-card service — tables (see data-design.md, data-dictionary.yaml)

CREATE TYPE gift_card_status AS ENUM ('active', 'redeemed', 'expired');

CREATE TABLE gift_card (
    gift_card_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code           text NOT NULL,
    initial_amount numeric(12,2) NOT NULL CHECK (initial_amount > 0),
    balance        numeric(12,2) NOT NULL CHECK (balance >= 0),
    status         gift_card_status NOT NULL DEFAULT 'active',
    issued_at      timestamptz NOT NULL,
    expires_at     timestamptz NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE redemption (
    redemption_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gift_card_id  bigint NOT NULL REFERENCES gift_card (gift_card_id),
    amount        numeric(12,2) NOT NULL CHECK (amount > 0),
    order_ref     text NOT NULL,
    redeemed_at   timestamptz NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE event_outbox (
    outbox_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gift_card_id  bigint NOT NULL REFERENCES gift_card (gift_card_id),
    topic         text NOT NULL,
    payload       jsonb NOT NULL,
    attempt_count int NOT NULL DEFAULT 0,
    last_error    text,
    published_at  timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now()
);
