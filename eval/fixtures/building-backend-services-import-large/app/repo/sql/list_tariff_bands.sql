SELECT band_id, weekday_mask, start_minute, end_minute, rate_cents_per_block
FROM tariff_band
WHERE tariff_id = %(tariff_id)s
ORDER BY start_minute, band_id;
