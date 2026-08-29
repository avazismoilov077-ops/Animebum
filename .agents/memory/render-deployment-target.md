---
name: Render deployment target
description: How to diagnose a Render bot that keeps showing an older version after GitHub pushes.
---

Before debugging code when a Render deployment still shows an old UI or behavior, verify that the active Render service belongs to the expected account and is connected to the same GitHub repository and branch.

**Why:** A different Render account or service can continue running the old deployment even though the current workspace and GitHub repository contain the new code.

**How to apply:** Check the active Render service, repository, branch, and latest deploy commit before making repeated code changes.