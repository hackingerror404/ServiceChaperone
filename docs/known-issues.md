# Known issues

| Issue | What it means for you | Planned fix | Also marked in |
| --- | --- | --- | --- |
| **Runs in the foreground only** | You start it by hand with `service-chaperone run` and it stops when the terminal closes. | M2: run as a systemd user service | `run` command help |
| **State is kept in memory** | After a restart, Service Chaperone forgets what was down, so a service that was already down alerts again. | Roadmap: save state and history in SQLite | the engine module |
| **No connectivity self-check** | If your own internet drops, every service looks down and you get an alert for each. | M2: connectivity self-check | the engine module |
| **Desktop notifications only** | No popup appears on a headless machine or when you're away from it. | Roadmap: email alerts | `notify.py` |
| **Websites only** | Proxy and port monitors are refused with "not supported yet". | M2: proxy and TCP port checks | the config loader |
| **Needs `notify-send`** | Without the `libnotify` package, alerts fail (and are logged, not crashed). | Documented in `docs/setup.md` | `notify.py` |
| **No automated test suite** | Changes are checked by hand with the scripts in `dev/`. CI only confirms the package installs and runs. | Revisit when there's time | `docs/git-standards.md` |
| **Discord and Slack bots can't be monitored** | Only websites are watched. | Roadmap, starting with a spike | `docs/roadmap.md` |