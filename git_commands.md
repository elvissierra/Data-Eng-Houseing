# Common Workflows

## Start a Feature Branch
```bash
git fetch origin
git switch main
git pull --ff-only
git switch -c feat/<slug>
```

## Update Your Feature with Main
```bash
git fetch origin
git rebase origin/main
# resolve conflicts, then:
git rebase --continue
git push --force-with-lease
```

## Fixup Commit into Previous One
```bash
git commit --fixup=<hash>
git rebase -i --autosquash origin/main
```

## Cherry-Pick a Commit
```bash
git fetch origin other-branch
git cherry-pick <hash>
```

## Rename a Branch Locally & Remotely
```bash
git branch -m old-name new-name
git push origin -u new-name
git push origin --delete old-name
```

## Delete a Merged Local Branch
```bash
git branch -d feat/<slug>
```

# Git Cheat Sheet

## Basic Git Commands

### Setup and Config
- `git config --global user.name "Your Name"`  
  Set the name that will be attached to your commits.
- `git config --global user.email "youremail@example.com"`  
  Set the email that will be attached to your commits.
- `git config --global color.ui auto`  
  Enable helpful colorization of command line output.

### Creating Repositories
- `git init`  
  Initialize a new Git repository.
- `git clone <repo_url>`  
  Clone an existing repository from a remote server.

### Making Changes
- `git status`  
  Show the working tree status.
- `git add <file>`  
  Add file contents to the staging area.
- `git add .`  
  Add all changes in the current directory to the staging area.
- `git commit -m "Commit message"`  
  Commit staged changes with a message.
- `git commit -am "Commit message"`  
  Add and commit tracked files in one step.

### Branching and Merging
- `git branch`  
  List all branches.
- `git branch <branch_name>`  
  Create a new branch.
- `git checkout <branch_name>`  
  Switch to a branch.
- `git checkout -b <branch_name>`  
  Create and switch to a new branch.
- `git merge <branch_name>`  
  Merge the specified branch into the current branch.
- `git branch -d <branch_name>`  
  Delete a branch.

### Remote Repositories
- `git remote -v`  
  Show remote URLs.
- `git remote add <name> <url>`  
  Add a new remote.
- `git fetch <remote>`  
  Fetch changes from remote but don’t merge.
- `git pull <remote> <branch>`  
  Fetch and merge changes from remote branch.
- `git push <remote> <branch>`  
  Push local branch to remote.

### Undoing Changes
- `git reset --hard HEAD`  
  Discard all local changes in working directory.
- `git reset <file>`  
  Unstage a file.
- `git checkout -- <file>`  
  Discard changes in working directory for a file.
- `git revert <commit>`  
  Create a new commit that undoes the changes from a previous commit.

### Viewing History
- `git log`  
  Show commit logs.
- `git log --oneline --graph --decorate --all`  
  Show a graph of the commit history.

## Context and Best Practices

- **Commit Often:** Make small, frequent commits with clear messages.
- **Write Good Commit Messages:** Use the imperative mood, be concise but descriptive.
- **Use Branches:** Keep your main branch clean by doing development work in feature branches.
- **Pull Before You Push:** Always pull remote changes before pushing to avoid conflicts.
- **Avoid Committing Sensitive Data:** Never commit passwords or secrets.
- **Use `.gitignore`:** Ignore files that should not be tracked (e.g., build files, logs).
- **Review Before Commit:** Use `git status` and `git diff` to review changes.
- **Use Tags:** Tag releases or important commits for easy reference.
- **Backup Your Work:** Push to remote repositories regularly.
- **Learn to Resolve Conflicts:** Understand how to handle merge conflicts effectively.

## Dos and Don'ts

### Dos
- Do keep your repository clean and organized.
- Do use descriptive branch names.
- Do review your changes before committing.
- Do update your local repository frequently.
- Do test your changes before pushing.

### Don'ts
- Don’t commit large binary files.
- Don’t commit generated or temporary files.
- Don’t commit directly to the main branch without review.
- Don’t ignore merge conflicts.
- Don’t forget to pull updates from the remote repository.

This cheat sheet covers the essentials to get started and maintain a healthy Git workflow. For more advanced usage, refer to the official Git documentation.
