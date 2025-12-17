# Forking yelp-mcp Submodule

This guide explains how to fork the `yelp-mcp` submodule so you can make changes and commit them to your own GitHub repository.

## Current Status

The submodule has been configured to point to your fork: `https://github.com/philmui/yelp-mcp.git`

## Steps to Complete the Fork

### Step 1: Create the Fork on GitHub

**Option A: Fork the Repository (Recommended)**
1. Go to https://github.com/Yelp/yelp-mcp
2. Click the "Fork" button in the top right corner
3. Select your account (`philmui`) as the destination
4. This creates: `https://github.com/philmui/yelp-mcp`

**Option B: Create a New Repository**
1. Go to https://github.com/new
2. Create a new repository named `yelp-mcp`
3. **Do NOT** initialize with README, .gitignore, or license
4. Copy the repository URL: `https://github.com/philmui/yelp-mcp.git`

### Step 2: Push Current Code to Your Fork

Once your fork exists on GitHub, push the current code:

```bash
cd yelp-mcp
git push -u origin main
```

If you get an error that the repository doesn't exist, wait a few minutes for GitHub to create it, then try again.

### Step 3: Verify the Fork

```bash
cd yelp-mcp
git remote -v
# Should show:
# origin  https://github.com/philmui/yelp-mcp.git (fetch)
# origin  https://github.com/philmui/yelp-mcp.git (push)

git log --oneline -1
# Should show the latest commit
```

### Step 4: Commit the Submodule Configuration Change

```bash
cd ..
git add .gitmodules
git commit -m "Update yelp-mcp submodule to point to fork"
```

## Making Changes to the Fork

Now you can make changes to `yelp-mcp` and commit them:

```bash
cd yelp-mcp

# Make your changes
# ... edit files ...

# Commit and push
git add .
git commit -m "Your change description"
git push origin main

# Update the parent repository to reference the new commit
cd ..
git add yelp-mcp
git commit -m "Update yelp-mcp submodule to latest"
git push
```

## Keeping Your Fork Updated

To sync your fork with the original Yelp repository:

```bash
cd yelp-mcp

# Add the original repository as upstream
git remote add upstream https://github.com/Yelp/yelp-mcp.git

# Fetch updates from upstream
git fetch upstream

# Merge upstream changes
git merge upstream/main

# Push to your fork
git push origin main
```

## Troubleshooting

**Error: "repository not found"**
- Make sure you've created the fork on GitHub first
- Check that the repository name matches exactly: `yelp-mcp`

**Error: "remote origin already exists"**
- The remote is already configured correctly
- Just proceed to push: `git push -u origin main`

**Want to keep upstream as a remote too?**
```bash
cd yelp-mcp
git remote add upstream https://github.com/Yelp/yelp-mcp.git
git remote -v
# Now you have both origin (your fork) and upstream (original)
```

