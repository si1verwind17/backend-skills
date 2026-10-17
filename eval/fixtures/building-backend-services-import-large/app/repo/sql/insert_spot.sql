-- The spot type is given by code; an unknown code inserts nothing (the
-- SELECT yields no row), which the repo reports as UnknownSpotType.
INSERT INTO spot (garage_id, code, spot_type_id, level, created_at, updated_at)
SELECT %(garage_id)s, %(code)s, st.spot_type_id, %(level)s, %(now)s, %(now)s
FROM spot_type st
WHERE st.code = %(spot_type)s
RETURNING spot_id;
