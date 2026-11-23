SELECT EXISTS (SELECT 1 FROM garage WHERE garage_id = %(garage_id)s) AS present
