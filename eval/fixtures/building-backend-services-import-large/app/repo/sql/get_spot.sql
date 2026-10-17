SELECT s.spot_id, s.garage_id, s.code, st.code AS spot_type, s.level, s.is_active,
       s.created_at, s.updated_at
FROM spot s
JOIN spot_type st ON st.spot_type_id = s.spot_type_id
WHERE s.spot_id = %(spot_id)s;
