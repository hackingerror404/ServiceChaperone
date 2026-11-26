# Running Service Chaperone in the background (systemd)

Running `service-chaperone run` in a terminal stops monitoring as soon as you close the window. On Linux, you can install it as a **systemd user service** so it starts automatically, logs to the systemd journal, and restarts itself if it crashes.

## Prerequisites

Before setting up the service, complete steps 1–5 of [docs/setup.md](setup.md):

1. `service-chaperone --version` works (installed with `pipx` into `~/.local/bin/service-chaperone`).
2. `~/.config/service-chaperone/config.toml` exists and works when tested with `service-chaperone run`.

## Install and start the service

Copy the unit file into your user systemd directory and reload systemd:

```bash
mkdir -p ~/.config/systemd/user
cp docs/service-chaperone.service ~/.config/systemd/user/service-chaperone.service
systemctl --user daemon-reload
```

Start it now and enable it so it starts automatically at login:

```bash
systemctl --user enable --now service-chaperone
```

## Check status and logs

Check that the service is running:

```bash
systemctl --user status service-chaperone
```

View the check log in the systemd journal (add -f to follow live):
```bash
journalctl --user -u service-chaperone -f
```

Stop or restart the service:

```bash
systemctl --user stop service-chaperone
systemctl --user restart service-chaperone
```

If you edit `~/.config/service-chaperone/config.toml`, restart the service so it loads the new config.

## Starting at boot without logging in (lingering)

By default, systemd only starts user services when you log in, and stops them when you log out. On a home server, Raspberry Pi, or any machine that boots without someone logging in, enable lingering for your user:

```bash
loginctl enable-linger "$USER"
```

Confirm it is enabled:

```bash
loginctl show-user "$USER" -p Linger
```

You should see `Linger=yes`. To turn it back off later, run `loginctl disable-linger "$USER"`.

## Important limitations

- **State is not saved yet.** Service Chaperone keeps monitor state in memory. If the service restarts (after a reboot, a crash, or `systemctl --user restart service-chaperone`), it forgets what was already down. A service that is still down will trigger a new DOWN alert once it fails `retries + 1` checks again. Saving state in SQLite is on the roadmap.
- **Desktop notifications require a graphical session.** Alerts currently use notify-send, which needs an active desktop session. On a headless machine—or after a reboot with lingering enabled before anyone logs in—monitoring and logging to journalctl still work, but desktop popups will not appear (Service Chaperone logs a warning and keeps checking). Headless alert channels like email are on the roadmap.

## Updating or uninstalling the service

After updating the code with `pipx install --force .`, restart the service so it runs the new version:

```bash
systemctl --user restart service-chaperone
```

To remove the background service:

```bash
systemctl --user disable --now service-chaperone
rm ~/.config/systemd/user/service-chaperone.service
systemctl --user daemon-reload
```