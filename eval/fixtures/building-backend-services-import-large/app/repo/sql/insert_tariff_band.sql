INSERT INTO tariff_band (tariff_id, weekday_mask, start_minute, end_minute, rate_cents_per_block)
VALUES (%(tariff_id)s, %(weekday_mask)s, %(start_minute)s, %(end_minute)s, %(rate_cents_per_block)s)
RETURNING band_id, weekday_mask, start_minute, end_minute, rate_cents_per_block;
