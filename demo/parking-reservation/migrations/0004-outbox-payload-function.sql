-- The event payload of every outbox row, built in the statement that changes the state.
-- p_row is to_jsonb of the reservation row after the transition; timestamps render in the
-- session time zone, which the service pins to UTC.
CREATE FUNCTION outbox_payload(
    p_event_id    uuid,
    p_event_type  outbox_event_type,
    p_occurred_at timestamptz,
    p_row         jsonb
) RETURNS jsonb
LANGUAGE sql STABLE AS $$
    SELECT jsonb_build_object(
        'event_id',       p_event_id,
        'event_type',     p_event_type,
        'occurred_at',    p_occurred_at,
        'reservation_id', p_row -> 'public_id',
        'driver_id',      p_row -> 'driver_id',
        'garage_id',      p_row -> 'garage_id',
        'spot_id',        p_row -> 'spot_id',
        'window_start',   p_row -> 'window_start',
        'window_end',     p_row -> 'window_end',
        'checked_in_at',  p_row -> 'checked_in_at',
        'checked_out_at', p_row -> 'checked_out_at',
        'cancelled_at',   p_row -> 'cancelled_at'
    )
$$;

COMMENT ON FUNCTION outbox_payload(uuid, outbox_event_type, timestamptz, jsonb) IS 'Builds the event-catalog payload of an outbox row from the reservation row after a transition.';
