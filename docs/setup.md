# Setting up Service Chaperone

> **Status: placeholder.** The full setup guide will be written together with the first runnable build (Milestone 1 in the design document's implementation plan). Until then there is nothing to install, and steps written for code that doesn't exist yet would only be guesses.
>
> Progress on writing it is tracked in **[this](https://github.com/hackingerror404/ServiceChaperone/issues/5)** issue.

## What you'll need

The design already commits to this stack, so you can get ready now.

**To run Service Chaperone**

- A Linux machine that stays on, such as a desktop, a home server, or a Raspberry Pi, with **systemd** (the background service runs as a systemd user service) if you'd intend for it run without manually starting it.
- **Python 3** [minimum version to be confirmed with the first build] and **pipx**, which is how Service Chaperone will be installed
- **git**, to clone the repository

**What the project is built with**

| Part | Tool |
| --- | --- |
| Scheduling checks | APScheduler |
| Website and proxy checks | httpx |
| Storage | SQLite, through SQLAlchemy |
| Alerts | Apprise (desktop notifications, email) |
| Status window | Flet |
| Discord bot monitoring | discord.py (a watcher bot; depends on the Discord spike result) |
| Slack bot monitoring | slack.py (same as the above) |

**Only if you use these features**

- **Email alerts:** an SMTP account to send from
- **Discord bot monitoring:** a free bot token from the Discord Developer Portal, with the presence intent enabled, and a server where the watcher bot and the bot you want to monitor are both members
- **Slack bot monitoring**: A similar server/group setup with the discord bots, and any additional bot tokens that a spike will need to confirm.

## In the meantime

You can still help while this is a placeholder. Read the [contributing guide](../CONTRIBUTING.md), browse the open issues, or open one to report a problem or suggest an idea.