"""
Tests for config.py and the command-line entry point
"""

import pytest

from protest_alerts import __main__ as entry
from protest_alerts import config
from protest_alerts.config import RfqEntry, Settings

ENV = {"RFQ_LIST": "123456789:My RFQ", "MS_URL": "https://webhook.example.com"}


def test_parse_rfq_list():
    result = config.parse_rfq_list(
        "123456789:My RFQ, 098765432 : Your RFQ ,555:Name: with colon"
    )

    assert result == [
        RfqEntry("123456789", "My RFQ"),
        RfqEntry("098765432", "Your RFQ"),
        RfqEntry("555", "Name: with colon"),
    ]


def test_parse_rfq_list_empty():
    assert config.parse_rfq_list("") == []
    assert config.parse_rfq_list("  ") == []


def test_parse_rfq_list_invalid():
    with pytest.raises(ValueError) as exc_info:
        config.parse_rfq_list("111:RFQ One,123456789")

    # Entries are secrets, so the error names the position, not the value
    assert str(exc_info.value) == "Invalid RFQ entry #2: expected NO:NAME"
    assert "123456789" not in str(exc_info.value)


def test_settings_from_env():
    settings = Settings.from_env(mode="roundup", env=ENV)

    assert settings == Settings(
        rfqs=(RfqEntry("123456789", "My RFQ"),),
        ms_webhook_url="https://webhook.example.com",
        mode="roundup",
    )


def test_settings_from_env_rejects_bad_mode():
    with pytest.raises(ValueError):
        Settings.from_env(mode="weekly", env=ENV)


@pytest.mark.parametrize("mode", ["daily", "roundup"])
def test_run_passes_mode(mocker, mode):
    mocker.patch.dict("os.environ", ENV)
    mock_main = mocker.patch("protest_alerts.search.main")

    entry.run([mode])

    assert mock_main.call_args.args[0].mode == mode


@pytest.mark.parametrize("argv", [[], ["weekly"]])
def test_run_rejects_missing_or_bad_mode(mocker, argv):
    mock_main = mocker.patch("protest_alerts.search.main")

    with pytest.raises(SystemExit):
        entry.run(argv)

    mock_main.assert_not_called()


def test_settings_from_env_slack_only():
    settings = Settings.from_env(
        mode="daily",
        env={
            "RFQ_LIST": "123456789:My RFQ",
            "SLACK_URL": " https://hooks.slack.com/services/T/B/X ",
        },
    )

    assert settings.ms_webhook_url == ""
    assert settings.slack_webhook_url == "https://hooks.slack.com/services/T/B/X"


@pytest.mark.parametrize("env", [{}, {"MS_URL": "", "SLACK_URL": " "}])
def test_settings_from_env_requires_a_channel(env):
    with pytest.raises(ValueError, match="MS_URL, SLACK_URL"):
        Settings.from_env(mode="daily", env={"RFQ_LIST": "", **env})
