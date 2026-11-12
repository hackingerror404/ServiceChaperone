# MVP Plan: Service Chaperone v1

**Milestone:** M1, demo on Nov 18, 2026. **Last updated:** Nov 11, 2026.
**Tracker:** [Milestone 1](https://github.com/hackingerror404/ServiceChaperone/milestone/1) and the [SC Progress Board](https://github.com/users/hackingerror404/projects/1).

## 1. What's in

**The slice:** An administrator lists a website in a config file, starts Service Chaperone, takes that website down, and sees a desktop notification once the configured retries run out. A second notification will be seen when the site comes back.

**The M1 issues, in build order:**

1. Project skeleton: an installable package with tests and CI
2. Check a website: status code, response time, timeout
3. Send a desktop notification when a service goes down or recovers
4. Load monitors from a TOML config file
5. Run each monitor on its own schedule (`service-chaperone run`)
6. Decide up or down: retries and state changes
7. M1 demo walk-through

## 2. What's deferred

| Not in v1 | Where it went | Why |
| --- | --- | --- |
| Proxy and TCP port checks | M2 | More check types add nothing to what the website path proves about the engine. |
| Connectivity self-check (no false alarms when your own internet drops) | M2 | Needed for the 72-hour success criterion, which v1 does not claim. |
| Running as a background systemd service | M2 | v1 is started by hand. |
| Finishing the setup guide, 72-hour and multi-outage runs | M2 | They need the pieces above. |
| Saving state across restarts, a status command or window, uptime history | Roadmap | Time did not fit; all three are planned next. |
| Alerts by email | Roadmap | Small and a `good first issue`. |
| Discord and Slack bot monitoring | Roadmap | It needs a different skill set (a watcher bot built with discord.py) from the website and service side. A 2-hour spike is planned for Dec 3 to 9. |
| An automated test suite | Dropped for now | Changes are checked with the scripts in `dev/` and the evidence goes in each PR. |

**Throwaway corners inside what v1 keeps** are labeled so nobody mistakes scaffolding for structure. They're listed in [known-issues.md](known-issues.md) and marked in the code where they live:

- It runs in the foreground and must be started by hand.
- State is held in memory only, so a restart forgets what was down.
- Alerts are desktop-only, through `notify-send`.
- Only websites are supported.
- With no self-check, a dropped internet connection looks like every service going down.

**If time runs short:** Retry count stops being configurable and uses a fixed default of 2. If that is not enough, the recovery notification moves to M2.

## 3. What risk it addresses

The proposal's risk register has three risks. v1 treats them differently:

| Risk in the register | What v1 does | Evidence |
| --- | --- | --- |
| **Learning the Python dependencies leads to incompatibilities or takes far too long** | **Retires it for the core path.** | See below. |
| GUI development takes too long | Sidesteps it. v1 is terminal-only, which is the fallback the register already names. | The whole demo runs from a terminal. |
| Bot communication proves much harder than the rest | **Does not retire it.** Bots are deferred, and the risk stays open until the spike. | Nothing in v1 claims it. |

**Evidence that the dependency risk is retired:**

- `httpx`, the scheduler, and `notify-send` work together in one running program, not only in separate `dev/` scripts.
- The install passes the strict test: `pipx install .` from a fresh clone, following only `docs/setup.md`, then `service-chaperone run` works.
- The one major incompatibility so far is the following: Apprise's desktop plugin was disabled in a normal pip install, and the notifier now calls `notify-send` instead.

## 4. The demo plan

### The claims, ranked

The first is the one v1 most needs to prove.

**1. Need: an outage is detected and the administrator is told in time.**
- **Traces to** success criterion 1 (within the time limit set by the user, accounting for retries).
- **Evidence we'll see:** the timestamped log shows the last good check and the DOWN alert, and a screenshot shows the notification. Measured detection time sits inside the bound in 3 of 3 runs at demo settings, and once at the defaults.

**2. Technical: several sites are tracked independently, including at the same time.**
- **Traces to** the first part of success criterion 3 (multiple outages, none missed), for websites only. This is also what retires the dependency risk above, because it needs the scheduler, the checks, and the notifier working together.
- **What a working slice proves that a mockup can't:** with two sites listed, I take both down within seconds of each other and get one separate alert for each. A third, slow site (the fake server's `/slow` route) does not delay checks of the others, which shows in the log timestamps.
- **Evidence we'll see:** two DOWN log lines and two separate notifications, then two recoveries, with no repeated alerts while the sites stay down.

**3. Usability: someone other than me can get from clone to a first alert, unaided.**
- **Who tries it:** [name: a classmate or my review partner who runs Linux].
- **"Unaided" means:** they use only `docs/setup.md`, `config.example.toml`, and `docs/demo.md`. I stay silent and don't provide help of my own.
- **Evidence we'll see:** they reach a first notification in 20 minutes or less, and their stall points become issues. If no second person is available, I do it on a clean user account reading only the docs, and I say that plainly in the demo.

### What v1 does not claim

Success criterion 2 (no false alerts over 72 hours) and the 24-hour multi-outage run across different kinds of service are M2. They need the self-check and the proxy and port checks first.

### The falsifier

| If we saw this… | …we'd know |
| --- | --- |
| Two sites stopped together produce only one alert | State is shared between monitors, or one check blocks the other. The "separate sites" idea isn't working. |

### Demo script, in three lines

1. I show a config file listing two websites, each with its own interval, timeout, and retries, install the tool the way a user would, and start `service-chaperone run`. Checks scroll past in the log.
2. I stop both sites at once, and within the bound two separate desktop notifications appear, one per site, matching the DOWN lines in the log.
3. I restart them, each one announces its recovery once, and nothing repeats while they were down.

### Fallback

- **No internet needed:** both "websites" are local fake servers (`dev/fake_server.py`), so nothing depends on the venue's wifi.
- **Rehearsed setup:** the config, both servers, and two terminals are ready beforehand, on the machine the notifications were tested on. I run the full demo at least once the day before.
- **If popups don't show on a shared screen** (some screen sharing captures only a window): the log is the primary evidence, and I show the notifications from my rehearsal screenshots.
- **Last resort:** a recording of a successful rehearsal run, declared as a recording.