import pytest

from parking_reservation.config import ConfigError, load_settings

GOOD = {
    "DATABASE_URL": "postgresql://u:secret@h/db",
    "GCP_PROJECT": "my-project",
    "AUTH_AUDIENCE": "https://svc",
    "FRONT_END_SERVICE_ACCOUNT": "fe@x",
    "SCHEDULER_SERVICE_ACCOUNT": "sc@x",
}


def test_a_complete_environment_loads() -> None:
    assert load_settings(GOOD).gcp_project == "my-project"


@pytest.mark.parametrize("name", sorted(GOOD))
@pytest.mark.parametrize("value", [None, "", "   "])
def test_a_missing_or_blank_setting_is_refused_by_name(name: str, value: str | None) -> None:
    env = {k: v for k, v in GOOD.items() if k != name}
    if value is not None:
        env[name] = value
    with pytest.raises(ConfigError, match=name):
        load_settings(env)


def test_a_database_url_of_another_scheme_is_refused_without_echoing_it() -> None:
    with pytest.raises(ConfigError) as raised:
        load_settings({**GOOD, "DATABASE_URL": "mysql://u:secret@h/db"})
    assert "secret" not in str(raised.value)


def test_a_malformed_database_url_is_refused_without_echoing_it() -> None:
    with pytest.raises(ConfigError) as raised:
        load_settings({**GOOD, "DATABASE_URL": "postgresql://u:pw%zz@h/db"})
    assert "pw" not in str(raised.value)


def test_the_database_password_is_not_in_the_settings_repr() -> None:
    assert "secret" not in repr(load_settings(GOOD))


@pytest.mark.parametrize(
    "project", ["p", "My-Project", "1project", "has_underscore", "x" * 40, "-lead"]
)
def test_a_malformed_gcp_project_is_refused(project: str) -> None:
    with pytest.raises(ConfigError, match="GCP_PROJECT"):
        load_settings({**GOOD, "GCP_PROJECT": project})
