SELECT count(*) AS active_spots
FROM spot
WHERE garage_id = %(garage_id)s
  AND is_active;
