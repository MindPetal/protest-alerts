"""
Parse run settings and the solicitation input list.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

MODES = ("daily", "roundup")


@dataclass(frozen=True)
class RfqEntry:
    rfq_no: str
    name: str


@dataclass(frozen=True)
class Settings:
    rfqs: tuple[RfqEntry, ...]
    ms_webhook_url: str
    mode: str
    slack_webhook_url: str = ""
    days: int = 1

    @classmethod
    def from_env(cls, mode: str, env: Mapping[str, str] = os.environ) -> "Settings":
        """
        Read RFQ_LIST, optional DAYS, and at least one of MS_URL / SLACK_URL
        from the environment
        """
        if mode not in MODES:
            raise ValueError(f"Invalid mode '{mode}': expected one of {MODES}")

        ms_webhook_url, slack_webhook_url = read_webhook_urls(env)

        return cls(
            rfqs=tuple(parse_rfq_list(env["RFQ_LIST"])),
            ms_webhook_url=ms_webhook_url,
            mode=mode,
            slack_webhook_url=slack_webhook_url,
            days=int(env.get("DAYS", "1")),
        )


def read_webhook_urls(env: Mapping[str, str]) -> tuple[str, str]:
    """
    Read the MS Teams and Slack webhook URLs. Either may be blank, but not both.
    """
    ms_webhook_url = env.get("MS_URL", "").strip()
    slack_webhook_url = env.get("SLACK_URL", "").strip()

    if not ms_webhook_url and not slack_webhook_url:
        raise ValueError("Set MS_URL, SLACK_URL, or both")

    return ms_webhook_url, slack_webhook_url


def parse_rfq_list(rfq_list: str) -> list[RfqEntry]:
    """
    Parse 'NO:NAME,...' entries. Only the first ':' splits, so names may
    contain colons.
    """
    entries = []

    if not rfq_list.strip():
        return entries

    for n, pair in enumerate(rfq_list.split(","), start=1):
        if ":" not in pair:
            raise ValueError(f"Invalid RFQ entry #{n}: expected NO:NAME")

        rfq_no, rfq_nm = pair.split(":", 1)
        entries.append(RfqEntry(rfq_no.strip(), rfq_nm.strip()))

    return entries
