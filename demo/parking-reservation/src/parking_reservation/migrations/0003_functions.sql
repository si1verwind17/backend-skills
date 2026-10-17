-- Reservation event payload, one shape for all lifecycle events (EV payload, see architecture design).
CREATE FUNCTION reservation_event_payload(
    p_reservation_id bigint, p_event_id uuid, p_topic text, p_occurred_at timestamptz
) RETURNS jsonb LANGUAGE sql STABLE AS $$
    SELECT jsonb_build_object(
        'event_id', p_event_id,
        'topic', p_topic,
        'occurred_at', p_occurred_at,
        'reservation_public_id', r.public_id,
        'status', r.status,
        'driver_id', r.driver_id,
        'garage_code', g.code,
        'spot_label', s.label,
        'start_at', r.start_at,
        'end_at', r.end_at,
        'checked_in_at', r.checked_in_at,
        'checked_out_at', r.checked_out_at,
        'cancelled_at', r.cancelled_at)
    FROM reservation r
    JOIN garage g ON g.garage_id = r.garage_id
    JOIN spot s ON s.spot_id = r.spot_id
    WHERE r.reservation_id = p_reservation_id
$$;

-- Records one lifecycle event for a reservation in the same transaction as the change (W1-W4).
CREATE FUNCTION enqueue_reservation_event(
    p_reservation_id bigint, p_event_id uuid, p_topic text, p_now timestamptz
) RETURNS void LANGUAGE sql AS $$
    INSERT INTO outbox_event (event_id, topic, reservation_id, payload, updated_at)
    VALUES (p_event_id, p_topic, p_reservation_id,
            reservation_event_payload(p_reservation_id, p_event_id, p_topic, p_now), p_now)
$$;

-- W1: create a reservation on the first free spot in label order (collation "C"), idempotent on (driver, key).
-- Requires READ COMMITTED (the default): the per-garage lock only serializes creates when the free-spot
-- search takes a fresh snapshot after the lock wait. SQLSTATE 23P01 / 23505 escaping from here mean a
-- race the lock did not cover (same key, different garage); the caller retries the whole call once.
-- Outcomes: created | replayed | key_reused | no_spot | garage_not_found.
CREATE FUNCTION reserve_spot(
    p_garage_code text, p_driver_id text, p_idempotency_key text,
    p_start_at timestamptz, p_end_at timestamptz,
    p_public_id uuid, p_event_id uuid, p_now timestamptz
) RETURNS TABLE (outcome text, reservation_id bigint) LANGUAGE plpgsql AS $$
DECLARE
    v_garage_id bigint;
    v_existing reservation%ROWTYPE;
    v_spot_id bigint;
    v_reservation_id bigint;
BEGIN
    -- Serializes creates per garage; the exclusion constraint stays the backstop for R1/R2.
    SELECT g.garage_id INTO v_garage_id FROM garage g WHERE g.code = p_garage_code FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RETURN QUERY SELECT 'garage_not_found'::text, NULL::bigint;
        RETURN;
    END IF;

    SELECT * INTO v_existing FROM reservation r
     WHERE r.driver_id = p_driver_id AND r.idempotency_key = p_idempotency_key;
    IF FOUND THEN
        IF v_existing.garage_id = v_garage_id AND v_existing.start_at = p_start_at
           AND v_existing.end_at = p_end_at THEN
            RETURN QUERY SELECT 'replayed'::text, v_existing.reservation_id;
        ELSE
            RETURN QUERY SELECT 'key_reused'::text, v_existing.reservation_id;
        END IF;
        RETURN;
    END IF;

    SELECT s.spot_id INTO v_spot_id FROM spot s
     WHERE s.garage_id = v_garage_id
       AND NOT EXISTS (
           SELECT 1 FROM reservation r
            WHERE r.spot_id = s.spot_id AND r.status <> 'cancelled'
              AND tstzrange(r.start_at, r.end_at, '[)') && tstzrange(p_start_at, p_end_at, '[)'))
     ORDER BY s.label COLLATE "C", s.spot_id
     LIMIT 1;
    IF NOT FOUND THEN
        RETURN QUERY SELECT 'no_spot'::text, NULL::bigint;
        RETURN;
    END IF;

    INSERT INTO reservation (public_id, garage_id, spot_id, driver_id, idempotency_key,
                             start_at, end_at, updated_at)
    VALUES (p_public_id, v_garage_id, v_spot_id, p_driver_id, p_idempotency_key,
            p_start_at, p_end_at, p_now)
    RETURNING reservation.reservation_id INTO v_reservation_id;

    PERFORM enqueue_reservation_event(v_reservation_id, p_event_id,
                                      'parking-reservation-reserved-v1', p_now);
    RETURN QUERY SELECT 'created'::text, v_reservation_id;
END
$$;

-- W2-W4: guarded state change plus its event, as two statements so the payload sees the new state.
-- Returns true when the row was in p_from and is now in p_to; false means nothing changed and the caller
-- re-reads and classifies (repeat of the same call, illegal transition, or not the driver's reservation).
-- Check-in additionally requires p_now < end_at (R16).
CREATE FUNCTION transition_reservation(
    p_public_id uuid, p_driver_id text,
    p_from reservation_status, p_to reservation_status,
    p_topic text, p_event_id uuid, p_now timestamptz
) RETURNS boolean LANGUAGE plpgsql AS $$
DECLARE
    v_reservation_id bigint;
BEGIN
    IF (p_from, p_to) NOT IN (('reserved', 'checked_in'), ('checked_in', 'completed'), ('reserved', 'cancelled')) THEN
        RAISE EXCEPTION 'illegal transition % -> %', p_from, p_to;
    END IF;
    UPDATE reservation r
       SET status = p_to,
           checked_in_at = CASE WHEN p_to = 'checked_in' THEN p_now ELSE r.checked_in_at END,
           checked_out_at = CASE WHEN p_to = 'completed' THEN p_now ELSE r.checked_out_at END,
           cancelled_at = CASE WHEN p_to = 'cancelled' THEN p_now ELSE r.cancelled_at END,
           updated_at = p_now
     WHERE r.public_id = p_public_id AND r.driver_id = p_driver_id AND r.status = p_from
       AND (p_to <> 'checked_in' OR p_now < r.end_at)
    RETURNING r.reservation_id INTO v_reservation_id;
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    PERFORM enqueue_reservation_event(v_reservation_id, p_event_id, p_topic, p_now);
    RETURN true;
END
$$;
