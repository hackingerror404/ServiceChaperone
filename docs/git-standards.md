# Git Standards

How a change gets into this project. If you're contributing, this is how
we work; if you think a rule is wrong, open an issue and say why.

## Branch names
Convention: type/issue#-short-desc.  
Example: fix/038-fix-connectivity-bug
Why: the type narrows down what each branch is connected to at the start, and the issue number connects it to the linked issue in github for the coder.

## Commit messages
I will be following the seven rules, listed [here](https://cbea.ms/git-commit/). This will ensure that every commit has a clear and documented reason for its existence in the codebase.

## Pull requests
Pull requests should remain to about one logical change per request, with other issues moved to other branches & PRs.  
Their description must link to the issue the request is resolving, which will describe the problems in more detail. If the PR is made of multiple commits, a short summary will be needed.  
This method will ensure issues and PRs are easy to follow and a team can stay on top of the program's development.

## Review
As I am maintaining and writing this project by myself over the course of this class, I can use both a self-review checklist and Claude where possible to review my own code.  

## Merging
I will be using the squash-and-merge approach for PRs to accomodate for cases with more than one commit included. This will create a more easily navigatable project history for future users. I will need to merge on my own due to being a solo developer, but I can use the methods mentioned above. 

## Definition of done
A change is done when every item below is true. I'll confirm each one when I merge (for someone else's PR, during review), and the PR template carries the same checklist so it is visible on every PR.

1. **Acceptance criteria met.** Every acceptance criterion on the linked issue is true, and is ticked off in the issue. If one can't be met, the PR says which and why.
2. **Testing.** Testing should be documented or explained in the pull requests or commits, whereever makes the most sense as per each issue. Automatic testing could be a great addition in future roadmaps, but most will likely need to be by hand over the rest of 2026.
3. **Reviewed.** The PR has been reviewed before merging: the PR template checklist is fully ticked, and there is a review comment on the PR. For my own changes, that comment comes from the self-review checklist plus a review pass with Claude, with one line on what was flagged and what changed.
4. **Docs updated, or "no docs impact" stated.** "Docs updated" means: if the change alters anything a user types, sees, or must install (a command, a config option, an alert message, setup steps), the matching file in `docs/` (such as `config.md` or `setup.md`) or the README is changed in the same PR. If nothing like that changed, the PR description says "No docs impact." The reviewer checks the diff for one or the other.
5. **Merged by squash-and-merge**, with a commit message that follows the seven rules and ends with `Closes #N`.
6. **Runs on main.** The tests workflow is green on the merge commit on main. If the change affects how the program runs, I also follow the steps in `docs/demo.md` once on main.
7. **Tidy.** The issue is closed (by `Closes #N`), its card on the project board is in Done, and the branch is deleted (the repository deletes merged branches automatically). The diff contains no secrets, debugging leftovers, or stray files.