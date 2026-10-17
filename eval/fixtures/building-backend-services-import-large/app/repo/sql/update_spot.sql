-- Partial update. spot_type is a code; an unknown code leaves the type
-- unchanged here and is rejected by the service before this runs.
UPDATE spot s
SET spot_type_id = COALESCE(
        (SELECT st.spot_type_id FROM spot_type st WHERE st.code = %(spot_type)s::text),
        s.spot_type_id
    ),
    level = COALESCE(%(level)s, s.level),
    is_active = COALESCE(%(is_active)s, s.is_active),
    updated_at = %(now)s
WHERE s.spot_id = %(spot_id)s
RETURNING s.spot_id;
