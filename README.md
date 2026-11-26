**Service Chaperone** is a program to monitor self-hosted online services, such as proxies, websites, and Discord/Slack bots, designed to alert hobbyist and volunteer administrators when their services experience an outage.

**Current Status**: Service Chaperone installs, reads a config file, checks websites, proxies, and TCP ports on a schedule, pauses alerts when your own internet drops, shows desktop notifications on outages and recoveries, and can run in the background as a systemd user service.

**Quickstart**: Install it by following [docs/setup.md](docs/setup.md), copy `config.example.toml` to `~/.config/service-chaperone/config.toml` and list your services in it, then run `service-chaperone run`. To keep it running in the background at login or boot, see [docs/systemd.md](docs/systemd.md).

**How to Contribute**: Visit [this](/CONTRIBUTING.md) link to learn about the CONTRIBUTING process.

To view the project's license, click [here](/LICENSE).
To view the project's proposal, click [here](docs/proposal.md).  
To view the project's design, click [here](docs/design.md).
To view the project's test results, click [here](docs/test-results.md).