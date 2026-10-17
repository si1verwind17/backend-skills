SELECT event_id, topic, payload, attempts
FROM outbox_event
WHERE status = 'pending' AND NOT (event_id = ANY(%(excluded)s))
ORDER BY attempts, event_id
LIMIT %(limit)s
