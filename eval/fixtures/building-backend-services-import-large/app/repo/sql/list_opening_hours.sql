SELECT weekday, open_minute, close_minute
FROM opening_hours
WHERE garage_id = %(garage_id)s
ORDER BY weekday;
