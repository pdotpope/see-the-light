# see-the-light

Weekly GitHub Actions job that watches [The Lights Fest](https://thelightsfest.com/)
for new event locations/dates and emails a notification when one appears.

The site has no email subscription, RSS feed, or JSON API, so `scraper.py`
parses the static HTML event list at `register3.thelightsfest.com`, diffs it
against `state.json`, and only sends an email when a genuinely new event URL
shows up. `state.json` is committed back to the repo by the workflow after
each run.

## One-time setup

1. Enable 2FA on the sending Gmail account, then generate an App Password at
   `myaccount.google.com/apppasswords`.
2. Add three repo secrets (Settings → Secrets and variables → Actions), or via CLI:

   ```
   gh secret set GMAIL_USER
   gh secret set GMAIL_APP_PASSWORD
   gh secret set NOTIFY_EMAIL
   ```

   `GMAIL_USER` is the sending address, `NOTIFY_EMAIL` is the recipient
   (can be the same address), `GMAIL_APP_PASSWORD` is the 16-character
   App Password from step 1.

## Running it

The workflow runs automatically every Sunday. Trigger it manually anytime
from the Actions tab, or:

```
gh workflow run notify.yml
```
