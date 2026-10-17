UPDATE outbox_event
SET status = 'published', published_at = %(now)s, updated_at = %(now)s
WHERE event_id = ANY(%(event_ids)s) AND status = 'pending'
