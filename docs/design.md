# Service Chaperone — Design Document

| | |
|---|---|
| **Authors** | Hazel Hacking |
| **Reviewers** | [who reviewed it — a teammate, the instructor, a design-review partner] |
| **Status** | Draft |
| **Last updated** | 10/16/26 |
| **Links** | [proposal] · [repository](https://github.com/hackingerror404/ServiceChaperone) · [issue tracker](https://github.com/hackingerror404/ServiceChaperone/issues) |

## Revision history

*A design doc changes as the design does. Record each meaningful revision so a reader can tell what the doc said when a decision was made.*

| Date | Author | What changed |
|---|---|---|
| 10/16/26 | Hazel Hacking | Initial Draft completed for Monday. |

---

## 1. Context and scope

*One or two paragraphs. What is being built, for whom, and what landscape it sits in. Link the proposal instead of repeating it — a reader who needs the full argument can follow the link.*

## 2. Goals and non-goals

**Goals** — *what this design must achieve, stated so you could check them:*

- [goal]

**Non-goals** — *things a reasonable reader would expect this system to do, which it deliberately won't. Carry them over from the proposal; here they bound the design.*

- [non-goal]

## 3. System-context diagram

![diagram](/docs/DesignDiagram1.png)

## 4. Architecture and components

Service Chaperone is made of two processes sharing one SQLite file: a background daemon that does all the monitoring, and a read-only status window that only displays it. Closing the window does not stop the monitoring daemon.

| Component | Responsibility | Talks to | Interface (rough) |
|---|---|---|---|
| Scheduler | Reads the config file, syncs monitor definitions into the Store, and runs each monitor's check at its own interval. | Config file, Store, Check Runners | Function calls into the runners, APScheduler jobs, one per monitor |
| Check Runners | One small module per service type (website, proxy, TCP port, Discord/Slack watcher). Performs a single check and reports up or down with response time or error. | Outside services, State Engine | Function call in (monitor settings), result object out (up/down, milliseconds, error text) |
| State Engine | Records every result, counts consecutive failures, runs the connectivity self-check, and decides when a monitor changes state. | Store, reference hosts, Notifier | Function calls, SQL writes to the Store |
| Notifier | Delivers an alert for each state change and retries on failure. Falls back to a desktop notification if other channels fail. | Apprise, State Engine, Store | Function call (monitor, old state, new state), Apprise URLs from the config |
| Store | Holds monitor definitions, current state, check history, and alert records in one SQLite file. | State Engine, Scheduler, Status window | SQL through SQLAlchemy |
| Status window | Shows each monitor as up or down with its last check time, and a "monitor offline" banner when the self-check fails. | Store | Read-only SQL queries on a user-set time |

![diagram](/docs/DesignDiagram2.png)

### Core flow, traced end to end

*The single most important user action in your MVP, step by step through the components above. If the trace needs a component the table doesn't have, the table is wrong.*

In this example, a website goes down and the administrator is told. The monitor is set to a 60-second interval, 10-second timeout, and 2 retries (so 3 consecutive failures count as down).

1. Either systemd starts the daemon at boot, or the user manually starts the program, depending on their preference. The Scheduler reads the config file, writes each monitor into the Store, and registers one timer per monitor.
2. At the 60-second mark, the Scheduler calls the website Check Runner with the URL and timeout.
3. The Check Runner sends an HTTP request and returns a result: down, with the error "timeout."
4. The State Engine saves the result to the Store and raises the monitor's consecutive-failure count to 1. The monitor stays "up" for now.
5. Checks 2 and 3 fail the same way, so after the third failure, the threshold has been met.
6. The State Engine runs the connectivity self-check against two reference hosts. Both answer, so the problem is the website, not the administrator's connection.
7. The State Engine records the change from up to down in the Store and hands it to the Notifier.
8. The Notifier sends a preferred notification type (either local desktop, or an email through Apprise), and records each delivery in the Store.
9. The Status window reads the new state on its next refresh and shows the monitor in red.
10. When a later check succeeds, the State Engine records the change back to up, and the Notifier sends a "recovered" alert.

Worst-case detection time is (retries + 1) × interval + timeout, here about 3 minutes 10 seconds.

### The failure case

In this example, The administrator's own internet drops while monitoring is running, which makes every service look down at once.

1. Every Check Runner result starts failing across all monitors.
2. When the first monitor reaches its failure threshold, the State Engine runs the connectivity self-check. Both reference hosts fail to answer.
3. The State Engine does not mark any service down. It records a "monitor offline" event in the Store and stops counting failures toward down.
4. The Notifier sends one desktop notification, "Chaperone can't reach the internet; services are unverified."
5. The Status window shows a "monitor offline" banner instead of red monitors, so the administrator isn't told something false.
6. When the connection returns, the process can resume and future self-checks pass. The State Engine clears the offline event and starts failure counts fresh, so a service that really went down during the outage is still caught within a reasonable  detection time.

Two other failures follow the same principle of recording the truth and staying quiet when unsure:
- An alert channel fails (for example, the email server is down). The Notifier retries with a delay, falls back to the desktop notification, and records "alert not delivered" in the Store so the status window can show it.
- The daemon crashes or the machine reboots when not set to start with systemd. If systemd is set, it will restart the daemon. If not set, the user will need to manually restart the program on their next boot. In both scenario, the program reloads each monitor's last known state from the Store.

## 5. Data model

Two rules keep the state simple. The config file is the source of truth for what to monitor, and the database holds everything that was observed. Each table has exactly one writer, so two components never fight over the same row.

| Entity | Key fields | Relationships | MVP or roadmap |
|---|---|---|---|
| Monitor | name, type (website, proxy, port, discord), target, interval, timeout, retries | Has one MonitorState, many CheckResults | MVP |
| MonitorState | monitor, state (up, down, unknown), consecutive failures, state since, last check time | Belongs to one Monitor | MVP |
| CheckResult | monitor, checked at, ok, response time (ms), error text | Belongs to one Monitor | MVP |
| StateChange | monitor (empty for a monitor-wide event), type (down, recovered, monitor offline, monitor online), time | Belongs to one Monitor, or to none for offline events; has many AlertDeliveries | MVP |
| AlertDelivery | state change, channel (desktop, email, Discord), status (sent, failed), time, error text | Belongs to one StateChange | MVP |
| MaintenanceWindow | monitor, start, end | Belongs to one Monitor | Roadmap |

## 6. Technology choices and alternatives considered

*One block per significant decision. The alternative must be one a reasonable team would actually pick. Where you did real work to decide — a spike, a benchmark, a prototype — cite it; that evidence is the difference between a preference and a decision.*

### Decision: Run monitoring in a background daemon, with the status window as a separate read-only process

- Chosen: A systemd user service runs the Scheduler, Check Runners, State Engine, and Notifier. The Flet status window is a separate process that reads the shared SQLite file.
- Alternative considered: One Flet desktop application that runs the Scheduler inside itself and shows status in the same window. It is simpler to build and to package, and follows the building structure that many small desktop tools follow.
- Why the chosen option wins, given our goals: The core promise is that the administrator hears about an outage without having to remember anything. In the single-process version, closing the window, a GUI crash, or a logout silently ends all monitoring, which recreates the exact problem the project exists to solve. The daemon can also start at boot if the user specified, where it will be restarted by systemd after a crash, and it keeps working if the GUI is later replaced by a terminal view (the fallback already in the risk register). The cost is real: two processes to package, and a service file the user must install.
- Evidence: None yet, a one-hour spike is needed to install a minimal service that writes a timestamp to a file every minute, kill it, and confirm systemd restarts it and a second process can read the file while it is being written
- What would change our mind: If packaging the service turns out to be too brittle for the target users (for example, it needs steps they can't be expected to do), or if a tray-icon application proves to be what administrators actually want, we would merge into one process and accept that closing it stops monitoring.

### Decision: Detect Discord bot outages with a watcher bot that checks presence, not with heartbeats

- Chosen: A watcher bot, run by Chaperone and added to the same Discord server as the bot being monitored, connects to Discord's gateway and reports whether the monitored bot shows as online (discord.py, with the presence intent enabled).
- Alternative considered: Heartbeat monitoring, the method used by services like Healthchecks.io. Each monitored bot calls a unique URL every few minutes, and a missing call means it is down. It is simpler, needs no Discord permissions, and is better at proving the bot's own code is still running.
- Why the chosen option wins, given our goals: Chaperone runs on the administrator's own machine, usually behind a home router. A heartbeat needs the bot to reach in to that machine, which means port forwarding or a hosted relay, and the project is deliberately local and free. Heartbeats also require editing every monitored bot's code, which the administrator may not be able or willing to do. The watcher bot only makes outbound connections and requires no changes to the bot being watched. The tradeoff is accuracy: presence shows that a bot is connected to Discord, not that its commands still work, and a frozen bot can look online. This is a known limitation to state in the doc and in the proposal.
- Evidence: None yet. A spike on a future date will kill a test bot's process ten times and measure how long the watcher takes to notice. Green: median detection of 60 seconds or less with zero missed outages. Red: median over 3 minutes, or any outage never detected.
- What would change our mind: A red spike result. Then bot monitoring becomes heartbeat-only, limited to bots that can reach the machine on the same local network, and the feature moves from the MVP to the roadmap as already planned.

## 7. Risks and open questions

*What you don't know yet, stated honestly. Each open question gets an owner and a way to find the answer.*

| Risk or question | Why it matters | Owner | How we'll find out, and by when |
|---|---|---|---|
| [risk] | [consequence] | [name] | [spike / test / conversation — milestone] |

## 8. Implementation plan

*The build order at milestone altitude — not a task list. Start with the thinnest vertical slice through the core flow, then widen it.*

| Milestone | What works when it's done | Depends on |
|---|---|---|
| 1 | [the thinnest end-to-end slice] | — |

---

## Sign-off

*Who reviewed this version and agreed it is ready to build from.*

| Reviewer | Role | Date | Approved |
|---|---|---|---|
| [name] | [role] | [date] | ☐ |
