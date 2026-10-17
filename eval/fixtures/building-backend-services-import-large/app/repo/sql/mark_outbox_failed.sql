-- Records a failed publish attempt; the row stays unpublished and is
-- retried on the next scheduled run (architecture-design.md failure path
-- for write-path #7). attempt_count/last_error drive the stuck-row alert.
UPDATE billing_outbox
SET attempt_count = attempt_count + 1, last_error = %(error)s, updated_at = %(now)s
WHERE outbox_id = %(outbox_id)s;
