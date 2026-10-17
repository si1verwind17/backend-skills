SELECT s.spot_id, s.garage_id, s.code, st.code AS spot_type, s.level, s.is_active,
       s.created_at, s.updated_at
FROM spot s
JOIN spot_type st ON st.spot_type_id = s.spot_type_id
WHERE s.garage_id = %(garage_id)s
  AND (%(spot_type)s::text IS NULL OR st.code = %(spot_type)s::text)
  AND (%(include_inactive)s OR s.is_active)
ORDER BY s.level, s.code;
