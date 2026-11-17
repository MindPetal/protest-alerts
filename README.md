# GAO protest search and post to a chat channel
[![protest-alerts-build](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-build.yaml/badge.svg)](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-build.yaml) [![protest-alerts-run](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-run.yaml/badge.svg)](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-run.yaml) [![protest-roundup-run](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-roundup-run.yaml/badge.svg)](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-roundup-run.yaml)

GitHub Actions workflows and Python client to search government protest updates from the GAO website.

- [protest-alerts-run](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-alerts-run.yaml) pulls protest updates for specified solicitations each day and posts them to MS Teams, Slack, or both.
- [protest-roundup-run](https://github.com/MindPetal/protest-alerts/actions/workflows/protest-roundup-run.yaml) runs weekly and posts a roundup of all currently open GAO protests for every tracked solicitation. It is not date bound.

To run you must obtain and configure as actions repo secrets:

| Name | Value |
| ---- | ----- |
|`RFQ_LIST`| A comma separated string of solicitation numbers and names. The number is used to search GAO, the name is whatever you want to display. `123456789:My RFQ,098765432:Your RFQ` |
| `MS_URL`| MS Teams webhook URL. Optional if `SLACK_URL` is set. More info on setting up Teams webhooks: [Create incoming webhooks with Workflows for Microsoft Teams](https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498)|
| `SLACK_URL`| Slack incoming webhook URL. Create a new app and webhook at [api.slack.com/apps](https://api.slack.com/apps).|

Set `MS_URL`, `SLACK_URL`, or both. Results are posted to every channel that has a URL, and the run fails at startup if neither is set.

> [!CAUTION]
> `MS_URL` and `SLACK_URL` are sensitive values. Store them only as GitHub Actions repository secrets. Never commit them, paste them into issues, pull requests, logs, etc. Secrets are not copied when the repo is forked or cloned. Each organization must create its own webhooks. If either one is exposed, rotate it right away.

> [!NOTE]
> This process is not guaranteed to find all protest updates for solicitations you select! GAO sometimes posts protests that are back-dated. I.e. the date of the update on the website is not when it was actually posted to the site.

## Chat channels:
Posting is handled by one module per chat tool, each called from `main` in [search.py](src/protest_alerts/search.py):
- [teams.py](src/protest_alerts/teams.py) builds MS Teams Adaptive Cards.
- [slack.py](src/protest_alerts/slack.py) posts the same content to Slack.

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
uv run pytest
```

Install the Playwright browser (first time only):
```sh
uv run playwright install chromium
```

Put the settings in a gitignored `.env` file so the webhook URL stays out of your shell history:
```sh
# .env
RFQ_LIST='my-rfq-list'
MS_URL='my-ms-webhook-url'
SLACK_URL='my-slack-webhook-url'
```

Execute daily alert:
```sh
uv run --env-file .env protest-alerts daily
```

Execute roundup:
```sh
uv run --env-file .env protest-alerts roundup
```
