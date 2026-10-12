# Git for research work

You do not need to learn git's commands to use it with Claude Code. Ask in ordinary words, and Claude runs them for you.

Git keeps a record of the versions you choose to save in a project folder, with what changed and why. GitHub is a website that holds a copy of that record, so you can back it up off your computer and share it.

## What it gives a researcher

Every saved version stays available. If a change by you or Claude turns out to be wrong, you can restore an earlier version of the whole project or a single file. You can also ask what changed since last week, since you sent a version to a co-author, or since you last made the figures.

You can tie a figure, table or number to the exact version of the code that produced it. This is needed to reproduce a result. The paper template in this folder, `paper-CLAUDE.md`, does this.

Collaborators can work on the same project without emailing files, and each change records who made it. When a journal or reader asks for the code behind a paper, you have it in one place, with its history.

## The words

| Word | What it means | What to say to Claude |
|---|---|---|
| Repository (repo) | A project folder whose history git records | "Make this folder a git repository" |
| Commit | A saved version, with a short message explaining what changed and why | "Commit this" or "commit the new analysis" |
| Diff | The changes between two versions | "What has changed since yesterday?" |
| Revert | A new commit that reverses an earlier commit. The earlier commit stays in the history, so nothing is lost | "Undo the fitting change with a revert" |
| Branch | A separate line of work where you can try changes without changing the main version | "Try this on a branch" |
| Merge | Add a branch's changes to the main version | "That worked. Merge it" |
| Push | Send your commits to GitHub | "Push" or "put it on GitHub" |
| Pull | Get commits that others have pushed | "Pull the latest" |
| Clone | Copy a repository from GitHub onto your computer | "Copy this repository onto my computer" |
| `.gitignore` | A file listing the files git should leave out of its record | "Keep the data folder out of git" |
| Pull request | A proposal on GitHub to merge a branch, which collaborators can comment on first | "Open a pull request for this" |

## What goes in, and what stays out

Keep code and scripts, LaTeX source, notes, the decision log, small text files of settings, and anything else you want to recover or share. Git works best with text files, where it can show exactly which lines changed.

Keep these out of the repository and list them in `.gitignore`:

- Data with personal details, such as interview recordings or transcripts, and anything under an ethics protocol.
- Passwords, API keys and access tokens.
- Large data files and outputs that a script can regenerate.
- PDFs of subscription papers.

When you create a GitHub repository, you choose whether it is private or public. You can make a private repository public later. Treat anything pushed to a public repository as copied the moment it arrives.

If you ever push a key or password, change it. Deleting the file does not remove it from the history.

## A day's work

1. Start a session in the project folder. Claude reads the handoff file, `handoffs/CURRENT.md`, and checks the repository's state.
2. Work as usual. When a piece of work is finished and checked, ask Claude to commit it. That might mean a script runs, a section reads well, or a figure is right. Small commits with clear messages make the history useful.
3. Before trying something that may not work out, such as a different method or a section rewrite, ask Claude to create a branch. If it works, ask Claude to merge it. If it does not, the main version is unchanged.
4. At the end of the day, ask Claude to push your commits so that your work is backed up on GitHub.

Claude commits and pushes only when you ask. It asks before doing anything that would discard work, including overwriting what is on GitHub, discarding changes you have not committed, or deleting a branch.

## Setting up, once

1. Install git. On a Mac, it comes with Apple's command-line tools. Run `xcode-select --install` in Terminal, then check the installation with `git --version`.
2. Make a free account at github.com.
3. Install GitHub's command-line tool, which lets Claude create repositories and push for you. With Homebrew (a tool for installing software on a Mac, from brew.sh), run `brew install gh`, then `gh auth login`. This opens your browser so that you can sign in. The sign-in is yours to do. Claude never handles your password.
4. Tell git the name and email address to record on each commit: `git config --global user.name "Your Name"` and `git config --global user.email "you@example.org"`. GitHub can give you a private email address to use instead, in its email settings.
5. In a project folder, ask Claude: "Make this a git repository, with a `.gitignore` for the data and outputs, and put it on GitHub as a private repository".
