# Setting up Service Chaperone

> **Status:** Service Chaperone installs, reads a config file listing what to monitor, and checks websites, proxies, and TCP ports on a schedule—either in your terminal or in the background via systemd. It pauses alerts when your own internet drops and shows a desktop notification when a service goes down or recovers.

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
| `type` | yes | The kind of check: `"website"`, `"proxy"`, or `"port"`. |
| `url` | yes for `"website"`; optional for `"proxy"` (`https://example.com`); not allowed for `"port"` | The address to check. Start it with `http://` or `https://`. For a proxy monitor, this is the page fetched *through* the proxy—set it to a reliable page you trust, since if that page goes down the proxy will also report DOWN. |
| `proxy` | yes for `"proxy"`; not allowed for `"website"` or `"port"` | The proxy URL to test, starting with `http://` or `https://` (for example `http://127.0.0.1:3128` or `http://user:pass@host:port`). SOCKS proxies (`socks5://`) aren't supported yet. |
| `host` | yes for `"port"`; not allowed for `"website"` or `"proxy"` | The hostname or IP address to connect to (for example `127.0.0.1` or `example.com`, with no `http://`). |
| `port` | yes for `"port"`; not allowed for `"website"` or `"proxy"` | The TCP port number to connect to, as a whole number from `1` to `65535`. |
| `interval` | no (60) | Seconds between checks. |
| `timeout` | no (10) | Seconds to wait before a check counts as failed. |
| `retries` | no (2) | Extra failures allowed before a service is called down. A service is called DOWN after `retries` + 1 failed checks in a row, so one dropped request doesn't set off an alert. |

If your proxy needs a username and password: keep credentials out of shared files, bug reports, and git repositories. Lock down permissions on your config file so other accounts on the machine can't read it: `chmod 600 ~/.config/service-chaperone/config.toml`.

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
20:56:38 WARNING Another site: DOWN (HTTP 500 Internal Server Error)
20:57:38 WARNING Another site: DOWN (HTTP 500 Internal Server Error)
20:57:38 WARNING Another site is now DOWN after 3 failure(s) in a row (HTTP 500 Internal Server Error)
```

An `UP` line shows how long the site took to answer. A `DOWN` line says why. The line saying a site **is now DOWN** is the moment you get a desktop notification. When the site answers again, you'll see `has recovered` and get a second notification. Press **Ctrl-C** to stop. If a check is in progress, stopping can take a few seconds, up to the monitor's timeout.

**How alerts work:**

- **One alert per change.** You get one notification when a site goes down and one when it recovers, not one for every failed check.
- **Not instant, on purpose.** A site is called down after `retries` + 1 failed checks in a row, so the longest it can take is about `(retries + 1) × interval + timeout` seconds. With the defaults that's roughly 3 minutes.
- **Quiet at startup.** A site that is healthy when you start gives no notification. A site that is already down when you start is reported once it has failed enough checks.
- **Quiet when your own internet drops.** Before calling a remote service DOWN, Service Chaperone tries to reach `1.1.1.1:443` and `8.8.8.8:443`. If neither answers, it holds failure counts, pauses DOWN alerts, and shows one "Service Chaperone is offline" notification instead of flooding you. Once the connection returns, failure counts reset to zero and normal monitoring resumes. Targets on `127.0.0.1` or `localhost` skip this self-check.

To use a config file somewhere else:

```bash
service-chaperone run --config /path/to/config.toml
```

`service-chaperone run` stays in your terminal, so closing the terminal stops it. To run it in the background and start it automatically at login or boot, follow [docs/systemd.md](systemd.md). A few things don't work yet, such as remembering what was down across a restart; the [known issues](known-issues.md) list them all.

## Desktop notifications

Service Chaperone tells you about outages with a desktop notification, which uses the `notify-send` command. Test that it works on your machine before you rely on it:

```bash
notify-send "Test" "Hello"
```

If a popup appears, you're set. If you get `command not found`, install the package that provides it:

```bash
sudo apt install libnotify-bin   # Debian, Ubuntu
sudo dnf install libnotify       # Fedora
sudo pacman -S libnotify         # Arch
```

If the command runs but nothing appears, check that **Do Not Disturb** is off, since some desktops silently hide notifications while it's on. Otherwise your desktop's notification service isn't running, which is common on machines with no desktop session, such as a headless server. If `notify-send` is missing or fails while `run` is going, Service Chaperone logs a warning and keeps checking, but you won't see popups.

## Updating

pipx installs a copy of the code taken at install time, so pulling new changes isn't enough by itself. From the `ServiceChaperone` folder:

```bash
git pull
pipx install --force .
```

If you run Service Chaperone as a background service, restart it so it picks up the new version:

```bash
systemctl --user restart service-chaperone
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
| The log says `is now DOWN` but no popup appears | Run `notify-send "Test" "Hello"`. If that shows nothing, see [Desktop notifications](#desktop-notifications), including Do Not Disturb. Look for a `WARNING` about `notify-send` in the log. |
| A site is down but there's no alert yet | An alert needs `retries` + 1 failed checks in a row. Wait about `(retries + 1) × interval + timeout` seconds. With the defaults that's roughly 3 minutes. |
| `Service Chaperone is offline` (or `Service Chaperone appears offline (could not reach 1.1.1.1:443, 8.8.8.8:443)`) | Your machine lost internet access, so DOWN alerts are paused until it comes back. If your internet is working fine, your network or firewall may be blocking TCP port 443 to both `1.1.1.1` and `8.8.8.8` (see the [known issues](known-issues.md)). |

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

**Proxy check.** Starts its own local upstream server and stand-in proxies, with no internet needed:

```bash
python dev/try_proxy.py
```

The last line should read `Finished with 0 failure(s).` You can also run `python dev/fake_proxy.py --port 3128` by hand to test a live proxy monitor end to end.

**TCP port check.** Starts its own local listening and stalled sockets, with no internet needed:

```bash
python dev/try_port.py
```

The last line should read `Finished with 0 failure(s).`

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

**Up and down rules.** Feeds the engine made-up results and checks when it alerts. It needs no network and no server:

```bash
python dev/try_engine.py
```

The last line should read `19 of 19 checks passed.`

**Connectivity self-check.** Uses local sockets as fake reference hosts, with no internet needed:

```bash
python dev/try_connectivity.py
```

The last line should read `Finished with 0 failure(s).`



**Desktop notifications.** This one needs `notify-send` (see above):

```bash
python dev/try_notify.py
```

You should see two popups, two seconds apart: one saying the service is down, then one saying it has recovered.

Then read the [contributing guide](../CONTRIBUTING.md) for branches, commits, and pull requests.

## What's next

All core local monitoring features are in place. See the [roadmap](roadmap.md) for planned additions like saved history in SQLite, email alerts, and Discord/Slack bot monitoring.