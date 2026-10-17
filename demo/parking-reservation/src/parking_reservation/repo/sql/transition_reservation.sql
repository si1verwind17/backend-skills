SELECT transition_reservation(
    %(public_id)s, %(driver_id)s,
    %(from_status)s::reservation_status, %(to_status)s::reservation_status,
    %(topic)s, %(event_id)s, %(now)s) AS applied
