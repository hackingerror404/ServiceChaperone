**Service Chaperone** is a program to monitor self-hosted online services, such as proxies, websites, and Discord/Slack bots, designed to alert hobbyist and volunteer administrators when their services experience an outage.

**Current Status**: Service Chaperone installs, reads a config file, and checks websites on a schedule, logging each result. Alerts when a service goes down are the next piece, and the first complete version is due in early December.

**Quickstart**: Install it by following [docs/setup.md](docs/setup.md), copy `config.example.toml` to `~/.config/service-chaperone/config.toml` and list your sites in it, then run `service-chaperone run`. It logs the result of every check.

**How to Contribute**: Visit [this](/CONTRIBUTING.md) link to learn about the CONTRIBUTING process.

To view the project's license, click [here](/LICENSE).
To view the project's proposal, click [here](docs/proposal.md).  
To view the project's design, click [here](docs/design.md).