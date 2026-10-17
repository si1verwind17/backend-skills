SELECT min(created_at) AS oldest FROM outbox_event WHERE status = 'pending'
