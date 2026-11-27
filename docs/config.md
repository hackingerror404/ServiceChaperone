# Configuration reference

Service Chaperone reads a TOML file from `~/.config/service-chaperone/config.toml` by default (or `$XDG_CONFIG_HOME/service-chaperone/config.toml` if `XDG_CONFIG_HOME` is set). You can point to a different file with `service-chaperone run --config /path/to/config.toml`.

Start by copying `config.example.toml` from the repository and editing it.

## Alert destinations (`notify`)

Add a top-level `notify` list (above your `[[monitor]]` blocks) to send `DOWN` and recovery alerts to email or any other service supported by [Apprise](https://github.com/caronc/apprise). This works alongside desktop notifications and lets headless servers send alerts without a graphical session.

If `notify` is omitted, Service Chaperone sends desktop notifications only.

### Setting up email alerts

**Gmail (using an App Password):**

Gmail blocks regular account passwords over SMTP. Turn on 2-Step Verification in your Google Account, create an **App Password**, remove any spaces from the 16-character code, and add:

```ini, toml
notify = [
    "mailto://yourusername:16charapppassword@gmail.com",
]
```

By default, Apprise emails the same address. To send to a different recipient, append `?to=recipient@example.com`.

**Other email providers (custom SMTP):**

Use mailtos:// (SMTP with TLS) and specify your provider's SMTP host:

```ini, toml
notify = [
    "mailtos://user:app-password@smtp.example.com?to=you@example.com",
]
```

### Validation and security

- **Checked at startup**: Service Chaperone validates every `notify` URL with Apprise before monitoring begins. An invalid URL fails immediately with a clear error instead of failing mid-outage.
- **Secrets stay out of logs**: Passwords and tokens in `notify` URLs are never written to logs or error messages.
- **Lock down file permissions**: Because `config.toml` holds credentials, keep it out of git and restrict who can read it:

```bash
chmod 600 ~/.config/service-chaperone/config.toml
```

## Monitors `[[monitor]]`

Each [[monitor]] block (double brackets) defines one service to check.

| Field | Required? | What it means |
| --- | --- | --- |
| `name` | yes | Name shown in logs and alerts. |
| `type` | yes | `"website"`, `"proxy"`, or `"port"`. |
| `url` | yes for `"website"`; optional for `"proxy"` (`https://example.com`); not allowed for `"port"` | `http://` or `https://` address to check (or fetch through the proxy). |
| `proxy` | yes for `"proxy"`; not allowed for `"website"` or `"port"` | `http://` or `https://` proxy URL (for example `http://127.0.0.1:3128`). SOCKS proxies aren't supported yet. |
| `host` | yes for `"port"`; not allowed for `"website"` or `"proxy"` | Hostname or IP address (no `http://`). |
| `port` | yes for `"port"`; not allowed for `"website"` or `"proxy"` | TCP port number from `1` to `65535`. |
| `interval` | no (`60`) | Seconds between checks.
| `timeout` | no (`10`) | Seconds to wait before a check counts as failed. |
| `retries` | no (`2`) | Extra failures allowed before a service is declared DOWN (`retries + 1` consecutive failures trigger an alert). |