# Service Chaperone - Proposal

## Executive Summary

Hobbyist and volunteer administrators who run their own proxies, websites, and Discord bots usually have no way to know when one goes down, short of remembering to check by hand. The predictable result is outages that last for days or weeks, discovered only when a user complains, by which point the people the service exists for have already been let down. I interviewed an administrator of custom proxies and Discord bots, who described services staying down for days or weeks before they noticed, and no tool they'd found that would catch it sooner. Service Chaperone is a free, open source Linux program that runs quietly in the background on the administrator's own machine, checks each service on a schedule they choose, and alerts them by desktop notification or email when one goes down. The semester MVP monitors websites, proxies, network ports, and Discord bots, with per-service intervals and retries, a connectivity self-check that prevents false alarms when the administrator's own internet drops, and a simple status window, all tested over a 72-hour run against real services. Deliberately out of scope: cloud or hosted deployment, and Windows or Mac support. What remains after the MVP, such as Slack bots, editing monitors in the GUI, uptime history, and maintenance windows, is real work a contributor can pick up without renegotiating the core.

## Problem & Users

**Who:** Individual administrators and small volunteer teams who run a handful of custom online services, such as websites, proxies, or Discord and Slack bots, without a dedicated operations team or a budget for monitoring. These users are technically comfortable: they mostly work on Linux, are at home in a terminal, can edit a configuration file, and have a machine that stays on, such as a desktop, home server, or Raspberry Pi. This is not for companies with on-call staff or existing monitoring platforms, which already have mature paid tools, nor for non-technical users who need a point-and-click setup.

**The need.** From one interview with an administrator who runs custom proxies and Discord bots, plus informal conversations with peers who run their own services:
1. Outages go unnoticed for days or weeks. [E] The interviewee described services staying down for days, and sometimes weeks, before they found out. As a recent example, a Discord bot that automatically deletes messages after 24 hours sent in a specific channel was out for 4 days before the interviewee noticed and could rectify.
2. The administrator finds out last. [E] Outages surfaced in only two ways: a manual checkup or a report from a user. In practice, the people the service exists to serve are acting as its alert system. 
3. Detection depends on memory. [E] The interviewee hasn't found any consistent solution, and remembering to check by hand is the only method they have. An outage gets caught exactly as fast as the administrator happens to think of it. 
4. The services that need watching aren't just web pages. [E] The interviewee's services are proxies and Discord bots. A monitor that only loads URLs would miss most of what they run. 
**Cost of the Status Quo:** [E] The administrator is not able to repair their services soon after they break, leading to users being unable to use the services for extended periods of time. [A] This did not have a financial cost to my interviewee as their services were provided as a volunteer status, but service outages can absolutely provide this cost if any finance or business actions occur through them. [A] It also erodes the trust of these services as consistent resources the user can rely upon, and that can deter users from using said services in the future.

## Solution Overview

A computer program that monitors the user’s custom services, as inputted into the program, on a specified timer to check them on a regular basis. The program will notify the administrator, either through a local computer notification or email, when it has detected an outage with any relevant data included in the message. By allowing the administrator to run this program on their local computer, it eliminates the need to manually check their services’ status and reduces the time an outage will affect users.

## Core Features

Prioritized. P0 is the MVP; P1 is the roadmap's first stop; P2 is an honest wishlist.

| Priority Level | Feature | Serves |
|---|---|---|
| P0 | Website checks: HTTP status and response time | Needs 1, 4 |
| P0 | Proxy and TCP port checks | Need 4 |
| P0 | Discord & Slack bot monitoring through a watcher bot | Need 4 |
| P0 | Per-monitor check interval, timeout, and retry count, set in a config file | Needs 1, 3 |
| P0 | HAlerts on state change (down and recovered) via desktop notification or email | Needs 1, 2 |
| P0 | Connectivity self-check before any alert | Trust |
| P0 | Background daemon that starts at boot as a systemd user service | Need 3 |
| P0 | Read-only status window showing each monitor's state and last check | Need 3 |
| P1 | Adding and editing monitors in the GUI | Adoption |
| P1 | Uptime percentages and outage history per monitor | Need 1 |
| P2 | Maintenance windows that pause alerts during planned downtime | Trust |

## Non-Goals

- Out-of-the-box server integration – the program could be at its “most ideal” when running on a separate server, such as AWS, rather than needing to run locally. However, this would drive up both the user cost and require the program to support this solution by default, adding a significant burden to the project scope.
- Porting the program to run natively on Windows / Mac – these operating systems require different standards than a native Linux program would, and aren’t the priority given that many services run on Linux servers to begin with.

## Technical Approach
| Choice | Explanation |
|---|---|---|
| Python 3, with APScheduler for scheduling and httpx for checks. | I have prior experience with Python projects completed for class and my personal portfolio. APScheduler handles per-monitor intervals, so I don't write my own timing loop, and httpx supports timeouts and routing requests through a proxy, which is how proxy checks work. |
| A background daemon separate from the GUI, run as a systemd user service. | Monitoring that stops when someone closes a window isn't monitoring. The daemon starts at boot and runs silently. The GUI is a client that can be opened and closed freely. |
| SQLite for monitors and check history. | One file, no database server for the user to install or maintain. The data is small and written by a single process, which is the case SQLite is built for. |
| Apprise for notifications. | One library covers Discord, Slack, email, and Linux desktop notifications. Supporting a new channel becomes a config line instead of an integration I'd maintain alone. |
| A watcher bot (discord.py / slack.py) instead of heartbeats for bot monitoring. | Heartbeats require the monitored bot to reach the user's home computer, which sits behind a router. A watcher bot only makes outbound connections, so it works on any home network with no port forwarding. I’ll need to verify this with a spike in the future. |
| Connectivity self-check before any alert. | If the user's own internet drops, every service looks down at once. The app checks two reliable public hosts first and reports "monitor offline" instead of flooding the admin with false outages. Not optional. |
| Flet desktop GUI. | The target user is an admin on their own Linux machine, and a native window with a tray icon fits that better than a browser tab. I have experience using Flet for a personal portfolio project. |
| Distributed via pipx, $0 to run | No hosting, no accounts, no recurring cost for me or the user. An open source tool that costs money to run tends not to get run. |

**Learning plan.** I have experience with Flet and Python, but I will likely need time to refresh myself of its structure and functionalities [ ~4 Hours]. If it doesn't take, the fallback is a Textual terminal interface, which costs visual polish but keeps every feature, since the GUI is a separate client. The Discord / Slack communication, along with all service communication, is a subject I am not familiar with and will need to educate myself on.

## Risks

| Risk | Category | Mitigation |
|---|---|---|
| Bot communication proves to be a significant difficulty compared to the rest of the app functions. | Technical | If need be, I can gut bot communication from the services that this program supports, and ensure it’s a future addition rather than a required one. |
| GUI Development takes too long to develop into a clean interface. | Skill | If a fallback is needed, I’m aiming for the program to be entirely runnable from a terminal window. |
| Learning the Python dependencies needed for the program’s features can lead to incompatibilities or take far too long to finish the MVP. | Dependency | I can look into if any of the dependencies would have expected compatibility issues with eachother, and do the proper research to ensure I stay on top of the code functions so writing the program moves smoothly. |

## MVP Definition

**The budget:** The following estimates are based on timescale of 40 hours outside of class assignments, instead only working on the raw project. Learning takes 11 of those: refreshing Flet, APScheduler, httpx, and Apprise (~7), plus Discord's gateway and presence intents (~4). Testing against the success criteria takes [~5], and packaging as a systemd service installable with pipx takes [~3]. I'm reserving [~4] as buffer for the problems I haven't predicted. That leaves about [17] hours of feature code, and this MVP is sized against that.

**In:** website checks (HTTP status and response time), proxy checks (a request routed through the proxy), TCP port checks, and Discord/Slack bot monitoring. Each monitor has its own interval, timeout, and retry count, defined in a config file. The connectivity self-check runs before any alert. Alerts fire on state changes only, sent as a Linux desktop notification or an email through Apprise. Check results are stored in SQLite. The daemon runs as a systemd user service. A read-only Flet status window shows each monitor as up or down, with its last check time. The whole thing runs on my own Linux machine, monitoring real proxies and web servers alongside test services I take down on purpose.

**Out for now:** Adding and editing monitors in the GUI, uptime percentages and history charts, adding and editing monitors in the GUI. These are on the roadmap, not abandoned. The architecture already separates check types, so bot monitoring slots in as one more check type later.

**Vertical, not broad:** one user type (an administrator), one workflow (define a service, get alerted when it goes down, see that it came back), working end to end on real services.

## Success Criteria

1. A user is notified of their service crashing within a timely manner. – specifically within the time interval set by the user that the program will ping the service.
2. A user is not notified of any issues if their services do not experience an outage over a long testing period. – a testing period of around 72 hours should be solid.
3. A user can be notified of multiple service outages across different types and occurring at different times without the program missing any or failing to notify the user. – a testing period of 24 hours with multiple service outages will be a strong test.

All of these are required for a successful iteration of my program, so they are not in any specific order. The final, #3, is the most descriptive and fully-encompassing.
