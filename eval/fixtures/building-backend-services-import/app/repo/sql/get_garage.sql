SELECT garage_id, name, timezone
FROM garage
WHERE garage_id = %(garage_id)s;
