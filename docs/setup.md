# Setting up Service Chaperone

> **Status:** Service Chaperone installs, reads a config file listing what to monitor, and checks those websites on a schedule, logging each result. It doesn't send alerts yet: a desktop notification when a service goes down or recovers arrives in the next update. The program is an active work in progress and setup will adjust over time to reflect that. Progress is tracked in [issue #7](https://github.com/hackingerror404/ServiceChaperone/issues/7).

This guide gets Service Chaperone installed from a clone of the repository. If you want to work on the code, jump to [For contributors](#for-contributors-development-setup).

## What you'll need

| You need | Check with | Notes |
| --- | --- | --- |
| A Linux machine | | Any distribution. For real monitoring later, one that stays on (a desktop, home server, or Raspberry Pi) works best. |
| Python 3.11 or newer | `python3 --version` | |
| git | `git --version` | |
| pipx | `pipx --version` | Step 1 shows how to install it. |

## 1. Install pipx

pipx installs command-line programs into their own isolated environments, so they can't clash with anything else on your system. Skip this step if `pipx --version` already works.

```bash
sudo apt install pipx          # Debian, Ubuntu
sudo dnf install pipx          # Fedora
sudo pacman -S python-pipx     # Arch
```

Then run this once and **open a new terminal**, so your shell can find programs that pipx installs:

```bash
pipx ensurepath
```

On another distribution, follow [pipx's own installation guide](https://pipx.pypa.io/stable/installation/).

## 2. Clone the repository

```bash
git clone https://github.com/hackingerror404/ServiceChaperone.git
cd ServiceChaperone
```

## 3. Install

From inside the `ServiceChaperone` folder:

```bash
pipx install .
```

## 4. Check that it worked

```bash
service-chaperone --version
```

You should see:

```
service-chaperone 0.1.0
```

That's the install. Next, tell it what to watch.

## 5. Tell it what to watch

Service Chaperone reads a config file that lists the services to check. Copy the example from your clone of the repository (the folder you installed from) into the default location:

```bash
mkdir -p ~/.config/service-chaperone
cp config.example.toml ~/.config/service-chaperone/config.toml
```

Open `~/.config/service-chaperone/config.toml` in any text editor and replace the example sites with your own. Each `[[monitor]]` block (with double brackets) is one thing to watch:

| Field | Required? | What it means |
| --- | --- | --- |
| `name` | yes | How the service appears in the output. Pick something you'll recognise. |
| `type` | yes | The kind of check. Only `"website"` works for now. |
| `url` | yes | The address to check. Start it with `http://` or `https://`. |
| `interval` | no (60) | Seconds between checks. |
| `timeout` | no (10) | Seconds to wait before a check counts as failed. |
| `retries` | no (2) | Extra failures allowed before a service is called down. This is read from the file now, and takes effect when alerts arrive in the next update. |

The comments in the example file explain each field again. If you set `XDG_CONFIG_HOME`, the file goes in `$XDG_CONFIG_HOME/service-chaperone/` instead. To keep the file somewhere else, use `--config` (below).

## 6. Run it

```bash
service-chaperone run
```

It checks every monitor straight away, then again at each monitor's own interval, and prints one line per check:

```
20:55:38 INFO Watching 2 monitor(s). Press Ctrl-C to stop.
20:55:38 INFO My website: UP (55.8 ms)
20:55:38 WARNING Another site: DOWN (HTTP 500 Internal Server Error)
```

An `UP` line shows how long the site took to answer. A `DOWN` line says why. Press **Ctrl-C** to stop. If a check is in progress, stopping can take a few seconds, up to the monitor's timeout.

To use a config file somewhere else:

```bash
service-chaperone run --config /path/to/config.toml
```

For now `run` stays in your terminal and only logs what it finds, so closing the terminal stops it. Alerts and running in the background are on the way (see the [To-Do List](#to-do-list)).

## Desktop notifications

Service Chaperone will tell you about outages with a desktop notification, which uses the `notify-send` command. Test that it works on your machine:

```bash
notify-send "Test" "Hello"
```

If a popup appears, you're set. If you get `command not found`, install the package that provides it:

```bash
sudo apt install libnotify-bin   # Debian, Ubuntu
sudo dnf install libnotify       # Fedora
sudo pacman -S libnotify         # Arch
```

If the command runs but nothing appears, your desktop's notification service isn't running. That's common on machines with no desktop session, such as a headless server.

## Updating

pipx installs a copy of the code taken at install time, so pulling new changes isn't enough by itself. From the `ServiceChaperone` folder:

```bash
git pull
pipx install --force .
```

## Uninstalling

```bash
pipx uninstall service-chaperone
```

You can then delete the `ServiceChaperone` folder.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `service-chaperone: command not found` | Run `pipx ensurepath`, then open a new terminal. `pipx list` shows whether it's installed. |
| `pipx: command not found` | Do step 1. |
| `error: externally-managed-environment` | You ran plain `pip install` outside a virtual environment. Use `pipx install .` instead. |
| You changed code but nothing changed | pipx runs its own copy. Run `pipx install --force .` again, or use the contributor setup below. |
| `notify-send: command not found` | See [Desktop notifications](#desktop-notifications). |
| `config file not found: ...` | Do [step 5](#5-tell-it-what-to-watch). The message shows the exact path it looked in. |
| `service-chaperone: monitor 'My website': 'interval' must be ...` (or any message that names a monitor and a field) | A mistake in your config file. The message says which monitor and which field. Fix it and run again. |
| `no monitors found` | The config file has no `[[monitor]]` block. Check you used double brackets. |
| Every site shows `DOWN (connection error: ... Name or service not known)` or `... Temporary failure in name resolution` | The address can't be looked up: you may be offline, or the URL is misspelled. The example sites are placeholders, so replace them with your own. |
| `DOWN (connection error: ... Connection refused)` | The machine answered, but nothing is listening at that address and port. Check the URL, including the port. |
| `error: the following arguments are required: command` | Type `service-chaperone run`. |

If none of these fit, [open an issue](https://github.com/hackingerror404/ServiceChaperone/issues/new/choose) with the command you ran and the full output.

## For contributors: development setup

When you're changing code, use a virtual environment with an **editable install** instead of pipx. Your edits take effect immediately, with no reinstall.

```bash
git clone https://github.com/hackingerror404/ServiceChaperone.git
cd ServiceChaperone
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
service-chaperone --version
```

Run `pip install -e .` again only when you change `dependencies` or `[project.scripts]` in `pyproject.toml`. To leave the environment, run `deactivate`. Next time, just `source .venv/bin/activate`.

### Checking your changes

The project checks changes with small scripts in `dev/` rather than an automated test suite. Run the ones that match what you changed, and paste their output into your pull request.

**Website check.** Start the local test server in one terminal and run the checks in another:

```bash
python dev/fake_server.py            # terminal 1: leave it running
python dev/try_website_check.py      # terminal 2
```

The last line should read `6 of 6 scenarios passed.`

**Config loading.** Checks good and bad config files, and the example file:

```bash
python dev/try_config.py
```

The last line should read `25 of 25 cases passed.`

**Scheduling.** With the fake server running as above, this takes about a minute (add `--seconds 20` for a quicker run):

```bash
python dev/try_schedule.py
```

The last line should read `13 of 13 checks passed.`

**Desktop notifications.** This one needs `notify-send` (see above):

```bash
python dev/try_notify.py
```

You should see two popups, two seconds apart: one saying the service is down, then one saying it has recovered.

Then read the [contributing guide](../CONTRIBUTING.md) for branches, commits, and pull requests.

## To-Do List

- Getting a desktop alert when a service goes down or recovers (the checks and the notifications both exist; they get connected next)
- Running it as a background service that starts on its own

See the [roadmap](roadmap.md) for a more comprehensive list of where the project is heading over time.