from parking_reservation.core import event_topics


def test_topics_follow_the_naming_scheme_and_are_distinct() -> None:
    topics = [v for k, v in vars(event_topics).items() if k.endswith("_TOPIC")]
    assert len(topics) == len(set(topics)) == 4
    assert all(t.startswith("parking-reservation-") and t.endswith("-v1") for t in topics)
