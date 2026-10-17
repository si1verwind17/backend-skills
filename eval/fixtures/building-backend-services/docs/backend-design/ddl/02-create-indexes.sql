-- Gift-card service — indexes (see data-design.md index plan)

CREATE UNIQUE INDEX uq_gift_card_code ON gift_card (code);

CREATE UNIQUE INDEX uq_redemption_card_order ON redemption (gift_card_id, order_ref);

CREATE INDEX idx_gift_card_active_expiry ON gift_card (expires_at) WHERE status = 'active';

CREATE INDEX idx_redemption_gift_card ON redemption (gift_card_id);

CREATE INDEX idx_event_outbox_unpublished ON event_outbox (created_at) WHERE published_at IS NULL;
