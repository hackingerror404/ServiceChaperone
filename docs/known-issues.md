# Known issues

| Issue | What it means for you | Planned fix | Also marked in |
| --- | --- | --- | --- |
| **Runs in the foreground only** | You start it by hand with `service-chaperone run` and it stops when the terminal closes. | M2: run as a systemd user service | `run` command help |
| **State is kept in memory** | After a restart, Service Chaperone forgets what was down, so a service that was already down alerts again. | Roadmap: save state and history in SQLite | the engine module |
| **Self-check reference hosts are hardcoded** | Connectivity checks always probe `1.1.1.1:443` and `8.8.8.8:443`. On a restricted network that blocks both on port 443, remote outages will be held as "offline". | Roadmap: make reference hosts configurable in `config.toml` | `connectivity.py` |
| **Desktop notifications only** | No popup appears on a headless machine or when you're away from it. | Roadmap: email alerts | `notify.py` |
| **SOCKS proxies aren't supported** | `socks5://` (and other SOCKS schemes) are rejected at startup. Only `http://` and `https://` proxies work. | Roadmap / good first issue (needs an extra dependency) | `config.py` |
| **Environment proxy variables are ignored** | Website checks ignore `HTTP_PROXY`, `HTTPS_PROXY`, and similar shell variables so each monitor checks exactly what is in `config.toml`. | By design | `checks/website.py` |
| **Needs `notify-send`** | Without the `libnotify` package, alerts fail (and are logged, not crashed). | Documented in `docs/setup.md` | `notify.py` |
| **No automated test suite** | Changes are checked by hand with the scripts in `dev/`. CI only confirms the package installs and runs. | Revisit when there's time | `docs/git-standards.md` |
| **Discord and Slack bots can't be monitored** | Only websites, proxies, and TCP ports are watched. | Roadmap, starting with a spike | `docs/roadmap.md` |