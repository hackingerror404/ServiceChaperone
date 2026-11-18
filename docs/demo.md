# Demo walk-through

A five-minute demo of what Service Chaperone does today, using two small web servers on your own machine. Nothing here needs the internet. Follow it exactly: every step says what you should see.

**What it shows:** an administrator lists two websites in a config file, starts Service Chaperone, and takes both sites down at once. A separate desktop notification appears for each. When the sites come back, each announces its recovery once.

## Before you start

- [ ] Service Chaperone is installed ([setup guide](setup.md)) and `service-chaperone --version` works.
- [ ] `notify-send "Test" "Hello"` shows a popup, and **Do Not Disturb is off**.
- [ ] You're in the folder you cloned (the one containing `docs/demo-config.toml`).
- [ ] You have **three terminal windows** open side by side. They're called Terminal 1, 2, and 3 below.
- [ ] If you're sharing your screen: popups appear on the desktop, not inside a single shared window, so share the **whole screen**, or use the log as your evidence.

## What the config says

`docs/demo-config.toml` lists two sites. Each is checked every 5 seconds, a check fails after 3 seconds, and a site is called down after 2 failed checks in a row (`retries = 1`).

```
Site A  ->  http://127.0.0.1:8001/
Site B  ->  http://127.0.0.1:8002/
```

So the longest an outage can go unnoticed is **(1 + 1) × 5 + 3 = 13 seconds**. It's usually 5 to 10.

## Steps

### 1. Start the two "websites"

In **Terminal 1**:

```bash
python3 -m http.server 8001 --bind 127.0.0.1
```

In **Terminal 2**:

```bash
python3 -m http.server 8002 --bind 127.0.0.1
```

Each prints `Serving HTTP on 127.0.0.1 port ...`. Leave them running.

### 2. Start Service Chaperone

In **Terminal 3**, from the cloned folder:

```bash
service-chaperone run --config docs/demo-config.toml
```

You should see both sites checked straight away, then again every 5 seconds:

```
03:57:55 INFO Watching 2 monitor(s). Press Ctrl-C to stop.
03:57:55 INFO Site A: UP (46.6 ms)
03:57:55 INFO Site B: UP (43.0 ms)
03:58:00 INFO Site B: UP (47.0 ms)
03:58:00 INFO Site A: UP (51.4 ms)
```

No popups yet, because nothing is wrong.

### 3. Take both sites down

Press **Ctrl-C** in Terminal 1, then in Terminal 2 (a few seconds apart is fine). Watch Terminal 3 and your desktop. Within 13 seconds you should see:

```
03:58:05 WARNING Site A: DOWN (connection error: [Errno 111] Connection refused)
03:58:05 WARNING Site B: DOWN (connection error: [Errno 111] Connection refused)
03:58:10 WARNING Site A: DOWN (connection error: [Errno 111] Connection refused)
03:58:10 WARNING Site A is now DOWN after 2 failure(s) in a row (connection error: ...)
03:58:10 WARNING Site B: DOWN (connection error: [Errno 111] Connection refused)
03:58:10 WARNING Site B is now DOWN after 2 failure(s) in a row (connection error: ...)
```

**Two separate popups:** "Site A is DOWN" and "Site B is DOWN".

Now wait about 20 seconds. The `DOWN` lines keep appearing, but **no new popups**: you get one alert per outage, not one per failed check.

### 4. Bring them back

In Terminals 1 and 2, press the up arrow and Enter to run the same server commands again. Within 5 seconds:

```
03:58:20 INFO Site A: UP (58.1 ms)
03:58:20 INFO Site A has recovered
03:58:20 INFO Site B: UP (55.0 ms)
03:58:20 INFO Site B has recovered
```

**Two more popups:** "Site A has recovered" and "Site B has recovered". After that, nothing repeats.

### 5. One at a time

Stop only Site B (Ctrl-C in Terminal 2). Site B alerts after the same few seconds, and **Site A stays quiet**, with `UP` lines carrying on. Restart Site B, and it announces its recovery.

### 6. Stop

Press **Ctrl-C** in Terminal 3. It prints `Stopping; waiting for any check in progress to finish.` and exits with no error text. Then stop the servers in Terminals 1 and 2.

## How long things take

| What happens | How long |
| --- | --- |
| A site goes down, then you get an alert | at most 13 seconds (usually 5 to 10) |
| A site comes back, then you get a recovery alert | at most 5 seconds |
| Repeat alerts while a site stays down | none |

## If something doesn't match

| What you see | What to do |
| --- | --- |
| The log says `is now DOWN` but no popup appears | Run `notify-send "Test" "Hello"`. If that shows nothing, check Do Not Disturb. The log lines are still your evidence. |
| `DOWN` never appears | The site didn't actually stop. Check with `ss -ltn \| grep 800`. |
| `Address already in use` starting a server | The old one is still running. Find and stop it, then try again. |
| Everything is `DOWN` from the start | The servers aren't running, or are on different ports. Redo step 1. |
| A step fails in front of other people | Use the log from your last good run, with the screenshots from your rehearsal. A recording of a successful run is the last resort: say it's a recording. |

## Extra: a hung site doesn't hold up the others

This shows that a site that never answers doesn't delay the checks of any other site. It needs the development setup (`dev/fake_server.py`).

1. Copy the config and add a third site to the copy:

   ```bash
   cp docs/demo-config.toml /tmp/demo-hang.toml
   cat >> /tmp/demo-hang.toml << 'TOML'

   [[monitor]]
   name = "Hung site"
   type = "website"
   url = "http://127.0.0.1:8765/slow"
   interval = 5
   timeout = 3
   retries = 1
   TOML
   ```

2. Start `python3 -m http.server` on 8001 and 8002 as in step 1, and in another terminal run `python dev/fake_server.py`. The `/slow` page waits a minute before replying.
3. Run `service-chaperone run --config /tmp/demo-hang.toml`.

The hung site times out every 5 seconds, and **Site A and Site B keep their own 5-second rhythm** alongside it:

```
03:59:15 WARNING Hung site: DOWN (timed out after 3s)
03:59:17 INFO Site A: UP (82.0 ms)
03:59:17 INFO Site B: UP (79.3 ms)
03:59:20 WARNING Hung site: DOWN (timed out after 3s)
03:59:20 WARNING Hung site is now DOWN after 2 failure(s) in a row (timed out after 3s)
```

You get one popup for the hung site, and none for A or B.

## Limits to know about

These are expected today and are listed in the [known issues](known-issues.md): there is no protection against your own internet dropping (every site would look down), state isn't remembered across a restart, and it runs in the foreground only.