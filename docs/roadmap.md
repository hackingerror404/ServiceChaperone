# Roadmap

Where Service Chaperone goes after the MVP (due Dec 2). Everything on this page is open for anyone to pick up, and most of it needs more hands than one person has.

Each item says how sure it is:

- **Planned:** I will build it, in this order, if nobody else gets there first.
- **Wanted:** worth doing, with no schedule.
- **Dream:** an idea with no promise attached.

The open items are issues labeled [`roadmap`](https://github.com/hackingerror404/ServiceChaperone/issues?q=is%3Aissue+is%3Aopen+label%3Aroadmap). To take one, comment on it, then see [CONTRIBUTING.md](../CONTRIBUTING.md).

## What the MVP is, and what was cut

The MVP watches websites, proxies, and TCP ports on a schedule you set, waits out one-off failures before alerting, stays quiet when your own internet drops, tells you by desktop notification, and runs as a systemd user service installed with pipx. Its known limitation: state isn't saved, so after a restart a service that is already down alerts again.

To fit the time that actually exists (about 15 hours of building per milestone, for one person), these were left out and moved here: saving state across restarts, a status view, Discord bot monitoring, alerts by email and chat, and uptime history. Leaving them out was a scheduling decision, not a judgment that they don't matter. A time-boxed 2-hour spike on Discord bot monitoring is planned for the final week (Dec 3 to 9), so that item starts with an answer instead of a guess.

## Next (planned, in this order)

### 1. Remember state and history
Keep each monitor's state and check history in SQLite, and reload it on startup so a restart doesn't repeat a DOWN alert.
**Why it matters:** it fixes the MVP's known limitation, and it's the foundation for items 4 and 5.
**Where to start:** the SQLite store issue, which points to the design document's data model.
**Good for:** someone who knows SQLAlchemy or wants to learn it.

### 2. Watch Discord bots
Detect when a Discord bot goes offline using a watcher bot, with no need for the bot to reach your machine.
**Why it matters:** it was the clearest need from the user interview, and the biggest thing left out of the MVP.
**Honest status:** it starts from the spike result. If the spike is green, this is a build; if it's red, the fallback is heartbeat monitoring. Read the spike issue first.
**Good for:** someone who has built a Discord bot and is familiar with the API + interface used by them.

### 3. Watch Slack bots
Detect when a Slack bot goes offline using a watcher bot, with no need for the bot to reach your machine.
**Why it matters:** it was the clearest need from the user interview, and the biggest thing left out of the MVP.
**Honest status:** it starts from the spike result. If the spike is green, this is a build; if it's red, the fallback is heartbeat monitoring. Read the spike issue first.
**Good for:** someone who has built a Slack bot and is familiar with the API + interface used by them.

### 4. See status at a glance
A `servicechaperone status` command first, then a read-only window.
**Why it matters:** right now, finding out what's up means reading the log.
**Open question:** which toolkit for the window (the proposal chose Flet; a terminal interface is a real alternative). Start by proposing one in the issue.
**Good for:** someone with UI experience.

### 5. Uptime percentages and outage history
Show how much of the time each service has been up, and list recent outages.
**Why it matters:** it answers "how reliable has this been?"
**Depends on:** item 2.
**Good for:** someone comfortable with SQL.

## Later (wanted, not scheduled)

- **Edit monitors inside the app** instead of editing a file.
- **SSL certificate expiry warnings** before a certificate lapses.
- **Keyword checks:** a page counts as down if it loads but is missing expected text.
- **Maintenance windows** that pause alerts during planned downtime.
- **Slack bot monitoring**, once Discord bot monitoring works.

## Potential long-term wants

- **Heartbeat monitors** for services that can call in to Service Chaperone, for people who can open a port.
- **Easier installs:** a `.deb`, an AUR package, or an AppImage.

## Not planned

These are deliberate non-goals, the same ones in the design document. If you think one is wrong, open an issue and say why.

- **Hosted or cloud deployment.** Chaperone is a local program with no hosting cost, and that is the point.
- **Windows and macOS.** The design leans on systemd and the target users work on Linux. If you want to own a port, open an issue to talk first.
- **Enterprise on-call features:** escalation, paging rotations, team accounts.

## How to help

1. Pick an item and look for its issue (or open one if it isn't there yet).
2. Comment to say you're taking it, so nobody doubles up.
3. Follow [CONTRIBUTING.md](../CONTRIBUTING.md). For anything bigger than a small fix, write a short note in the issue first about how you'd approach it.
