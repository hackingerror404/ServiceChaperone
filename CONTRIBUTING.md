# Contributing to Service Chaperone

Service Chaperone is a small, free Linux program that watches websites, proxies, ports, and messaging bots and tells you when one goes down. It is maintained by one person, so a good first contribution can be small: a bug report, a typo fix, or a test.

## Get started

If you do only one thing first, get Service Chaperone running on your own machine.

1. **Set up your environment.** Follow [docs/setup.md](docs/setup.md). It covers installing dependencies and starting the program.
2. **Run the tests.** The command is in `docs/setup.md`. If they don't pass on a fresh checkout, that's a bug. Please open an issue.
3. **Look at the open issues.** Read a few to get a feel for what's being worked on and how problems are described.
4. **Pick one and say so.** Comment on the issue that you're taking it, then start.

Not sure where to begin? Issues labeled `good first issue` are meant for newcomers. If you found a problem that isn't listed, open an issue first, even for a small fix.

## Picking work

Everything starts with an issue, so nobody builds the same fix twice.

- **Check before you start.** Search the issues to see whether your bug or idea is already there and whether someone is working on it.
- **Claim it.** Comment on the issue before you begin. If a claimed issue goes quiet for a few weeks, ask in the thread before taking it over.
- **No issue yet?** Open one that describes the problem and what you'd like to do. I'll reply before you spend time on it, which saves you from writing something I can't merge.

## Making a change

### Branches

Create a branch from `main` named `type/issue#-short-desc`. The type tells a reader what kind of work it is, and the issue number links it to the discussion.

```
fix/038-fix-connectivity-bug
```

Common types are `feat`, `fix`, `docs`, and `test`.

### Commit messages

Commits follow [the seven rules of a great commit message](https://cbea.ms/git-commit/). In short: a short imperative subject line, a blank line, and a body that explains *what* changed and *why*. Every commit should leave a clear record of its reason for existing.

### Pull requests

- **One logical change per pull request.** If you notice something else that needs fixing, put it on its own branch and PR.
- **Link the issue** the PR resolves in the description. The issue holds the detail about the problem, and the PR holds the detail about the fix.
- **Summarize multiple commits.** If the PR has more than one commit, add a short summary to the description.
- **Update the docs** if the program's behavior changes significantly.

Before you open the PR, read your own diff against this checklist:

- [ ] It does one thing, and the description links the issue.
- [ ] The program runs and the tests pass on your branch.
- [ ] Commit messages follow the seven rules.
- [ ] Docs are updated if behavior changed.
- [ ] No leftover debugging code, stray files, or secrets (tokens, passwords, webhook URLs).

## Review

Every pull request is reviewed by the maintainer before it merges, including my own. Reviews look at whether the change solves the linked issue, stays within one logical change, runs correctly, and is understandable to the next person who reads it. Comments are about the code, not the person, and you can push back if you disagree. I'll aim to respond within one week. For my own code I use the same checklist above and Claude as an extra pair of eyes, and you're welcome to do the same.

## Merging and done

Pull requests are merged with **squash and merge**, so each change becomes one clear entry in the project history, however many commits it took to get there. A change is done when it has been reviewed, merged, and runs on `main`. After that, the issue is closed and the branch is deleted.

## Why GPL-3.0

Service Chaperone is licensed under [GPL-3.0](LICENSE), and I chose it because I want this software to stay free, open, and documented for everyone who might need it, from one person running a Discord bot to a large company. GPL-3.0 is a copyleft license: anyone can use and modify the code however they like, but anyone who distributes a modified version has to share its source under the same license, so improvements can't be locked behind a paywall or absorbed into closed commercial software. The cost of that choice is that Service Chaperone can't become part of a closed, monetized product, and I accept that trade because a tool that tells you when something is down should be a net positive for anyone who can use it. The license doesn't require changes to come back to this project, so I'm asking instead: if you fix or improve something, open a pull request here so everyone benefits. By contributing, you agree that your contribution is released under GPL-3.0.