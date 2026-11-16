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

    @classmethod
    def from_env(cls, mode: str, env: Mapping[str, str] = os.environ) -> "Settings":
        """
        Read RFQ_LIST and MS_URL from the environment
        """
        if mode not in MODES:
            raise ValueError(f"Invalid mode '{mode}': expected one of {MODES}")

        return cls(
            rfqs=tuple(parse_rfq_list(env["RFQ_LIST"])),
            ms_webhook_url=env["MS_URL"],
            mode=mode,
        )


def parse_rfq_list(rfq_list: str) -> list[RfqEntry]:
    """
    Parse 'NO:NAME,...' entries. Only the first ':' splits, so names may
    contain colons.
    """
    entries = []

    if not rfq_list.strip():
        return entries

    for pair in rfq_list.split(","):
        if ":" not in pair:
            raise ValueError(f"Invalid RFQ entry '{pair}': expected NO:NAME")

        rfq_no, rfq_nm = pair.split(":", 1)
        entries.append(RfqEntry(rfq_no.strip(), rfq_nm.strip()))

    return entries
