# Communication and maintainer norms

How to reach me, what to expect back, and how decisions about Service Chaperone get made. These describe how I work while the project is active. If that changes, I'll update this page rather than quietly miss the promises on it.

## Where discussion happens

Everything happens on GitHub, in the open, where it can be linked to the code it's about.

- **Bugs and feature ideas:** open an issue using one of the forms.
- **Questions about using or contributing to Service Chaperone:** open an issue and ask. Someone else probably has the same question.
- **Code review:** on the pull request itself.
- **Conduct problems:** by email, not in public. See the [Code of Conduct](../CODE_OF_CONDUCT.md).

There is no chat server, mailing list, or Discussions tab. One place to watch is a place I can keep up with.

## Response times

| What | What you can expect |
| --- | --- |
| A new issue | A first reply within 7 days |
| A new pull request | A first review within 7 days |
| A conduct report | Acknowledged within 3 days (details in the Code of Conduct) |

A first reply isn't always an answer. It means I've read it and will say what happens next. If I can't meet a deadline, for example during exam weeks, I'll say so on the issue instead of going quiet. If you haven't heard from me after 7 days, a comment on the issue is welcome, not rude.

## How I know what's waiting

Every issue created through the bug or feature form gets the **`needs triage`** label automatically. I remove it once I've read the issue and replied, or closed it. At least every three days I check:

- **Issues waiting for a first reply:** `is:issue is:open label:"needs triage"`
- **Issues made without a form** (these get no labels at all): `is:issue is:open no:label`
- **Pull requests nobody has reviewed:** `is:pr is:open review:none`

Anything on those lists older than 7 days is overdue, and I treat it that way.

## Who maintains

Service Chaperone is maintained by me, [@hackingerror404](https://github.com/hackingerror404), as a solo developer. I review and merge every pull request, including my own, as described in the [contributing guide](../CONTRIBUTING.md). If more maintainers join, this page will say who they are and how work is divided.

## How decisions get made

1. **Ideas start as a feature request.** The form asks for the problem, who has it, and what you do today, because a clear problem can be solved in several ways.
2. **I decide against the project's goals.** The question is whether it serves the goals and fits within the non-goals in the design document, and whether it fits the time I have.
3. **I reply with one of three outcomes and the reason:** accepted (I'll build it, or it's open for you to build), deferred to the roadmap (labeled `roadmap`), or declined. This usually happens within two weeks of my first reply.
4. **Changes to the design get recorded.** If a decision changes the architecture, data model, or a goal, the design document is updated in a pull request, so the revision history shows what changed and why.