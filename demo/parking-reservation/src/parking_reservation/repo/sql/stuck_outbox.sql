SELECT event_id
FROM outbox
WHERE status = 'pending' AND attempts >= %(attempts)s
ORDER BY outbox_id
