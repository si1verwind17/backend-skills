-- Background publisher (write-path #7): claim a batch of unpublished rows.
-- FOR UPDATE SKIP LOCKED lets overlapping scheduler invocations run safely
-- without blocking each other on the same rows.
SELECT
    outbox_id, reservation_id, reservation_public_id, driver_id, garage_id, spot_id,
    window_start, window_end, completed_at, attempt_count
FROM billing_outbox
WHERE published_at IS NULL
ORDER BY created_at
LIMIT %(limit)s
FOR UPDATE SKIP LOCKED;
