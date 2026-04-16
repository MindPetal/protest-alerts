# GAO protest search and post to MS Teams
[![protest-alerts-build](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-build.yaml/badge.svg)](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-build.yaml) [![protest-alerts-run](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-run.yaml/badge.svg)](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-run.yaml)

Python client to scrape government protest updates from the GAO website for the prior day.

The [Protest-Alerts-Run](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-run.yaml) workflow pulls protest updates for specified solicitations each day and posts to a designated MS Teams channel. To run this you must obtain and configure as actions repo secrets:
- RFQ_LIST: A comma separated string of solicitation numbers and names
```
   123456789:My RFQ,098765432:Your RFQ
```
- MS_URL: MS Teams webhook URL for your organization.

More info on setting up Teams webhooks: [Create incoming webhooks with Workflows for Microsoft Teams](https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498)


## Local execution:

Python 3.13+ required. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (`brew install uv`) and sync dependencies:
```sh
uv sync --dev
```

Lint:
```sh
uv run ruff check .
uv run ruff format --check .
```

Git hook (auto-formats Python files on commit):
```sh
git config core.hooksPath hooks
```

Type check:
```sh
uv run ty check
```

Tests:
```sh
uv run pytest test_search.py
```

Execute: pass solicitation list, ms teams webhook url:
```sh
uv run python3 search.py my-rfq-list my-ms-webhook-url
```
