# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Wenget bucket - a curated collection of CLI tools and scripts for the [Wenget](https://github.com/superyngo/Wenget) package manager. The repository generates a `manifest.json` that Wenget uses to discover and install packages.

## Commands

### Generate manifest
```bash
# Using wenget binary (preferred)
./wenget bucket create -r sources_repos.txt -s sources_scripts.txt -o manifest.json

# With direct URLs
./wenget bucket create -d https://github.com/user/repo,https://gist.github.com/user/id
```

### Validate manifest
```bash
python3 -c "import json; d=json.load(open('manifest.json')); print(f'✓ {len(d[\"packages\"])} packages, {len(d.get(\"scripts\",[]))} scripts')"
```

## Architecture

### Source Files
- `sources_repos.txt` - GitHub repository URLs for binary packages (one per line, `#` for comments)
- `sources_scripts.txt` - Script source URLs (supports both Gist URLs and raw script URLs)
  - Gist URLs: Auto-extracts all scripts from each gist
  - Raw URLs: Direct links to script files

### Generated Output
- `manifest.json` - Contains `packages` array (binary releases from GitHub repos) and `scripts` array (from Gists), plus `last_updated` timestamp

### Wenget Binary
- `wenget` - Pre-compiled Wenget binary (Linux x86_64 musl) used for manifest generation
- Update manually from [Wenget Releases](https://github.com/superyngo/Wenget/releases)

### Archived (Legacy)
- `archive/scripts/` - Old Python-based generation scripts (no longer used)

### CI/CD
- `.github/workflows/update-manifest.yml` - Runs weekly (Monday), on manual trigger, or when source files change. Uses wenget binary to regenerate manifest.

## Adding Content

**Binary package**: Add GitHub repo URL to `sources_repos.txt` (requires binary releases with platform-specific assets)

**Script**: Add URL to `sources_scripts.txt`
- Gist URL: `https://gist.github.com/username/gist_id` (auto-extracts all .ps1, .sh, .bat, .cmd, .py scripts)
- Raw script URL: `https://raw.githubusercontent.com/user/repo/branch/path/script` (detects type from extension or shebang)

## Updating Wenget Binary

When a new version of Wenget is released:
1. Download the latest `wenget-linux-x86_64-musl.tar.gz` from releases
2. Extract and replace `./wenget` in repo root
3. Commit and push
