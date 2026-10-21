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
I will be using the squash-and-merge approach for PRs to accomodate for cases with more than one commit included. This will create a more easily navigatable project history for future users. I will need to merge on my own due to being a solo developer, but I can use the methods mentioned abover 

## Definition of done
A change will be done once it has been reviewed, merged, and runs on main. If behavior of the program is changed to a significant degree, my documentation will be updated. Issues will be closed and marked approprately, and branches will be deleted when fully merged.