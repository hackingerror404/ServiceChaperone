# Setting up Service Chaperone

> **Status:** Service Chaperone installs and reports its version, and its first building blocks (a website check and desktop notifications) exist, but it doesn't monitor anything yet. The program is an active work in progress and setup will adjust over time to reflect that. Progress is tracked in [issue #7](https://github.com/hackingerror404/ServiceChaperone/issues/7).

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

That's the whole install. The monitoring commands arrive in later releases (see [To-Do List](#to-do-list)).

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

**Desktop notifications.** This one needs `notify-send` (see above):

```bash
python dev/try_notify.py
```

You should see two popups, two seconds apart: one saying the service is down, then one saying it has recovered.

Then read the [contributing guide](../CONTRIBUTING.md) for branches, commits, and pull requests.

## To-Do List

- Writing a config file that lists what to monitor
- Running Service Chaperone and getting alerts
- Running it as a background service that starts on its own

See the [roadmap](roadmap.md) for a more comprehensive list of where the project is heading over time.