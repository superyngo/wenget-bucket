# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Wenget bucket - a curated collection of CLI tools and scripts for the [Wenget](https://github.com/superyngo/Wenget) package manager. The repository generates a `manifest.json` that Wenget uses to discover and install packages.

## Commands

### Generate manifest
```bash
python scripts/generate_manifest.py sources_repos.txt -s sources_scripts.txt -o manifest.json
```

### Validate manifest
```bash
python scripts/validate_manifest.py manifest.json
```

### Run test suite
```bash
bash scripts/test_scripts.sh
```

## Architecture

### Source Files
- `sources_repos.txt` - GitHub repository URLs for binary packages (one per line, `#` for comments)
- `sources_scripts.txt` - GitHub Gist URLs for scripts (auto-extracts all scripts from each gist)

### Generated Output
- `manifest.json` - Contains `packages` array (binary releases from GitHub repos) and `scripts` array (from Gists), plus `last_updated` timestamp

### Scripts
- `scripts/generate_manifest.py` - Fetches GitHub API to build manifest from source files. Uses `GITHUB_TOKEN` env var for API rate limits. Detects platforms using 4-component keyword matching (extension, platform, architecture, compiler). See [Platform Detection Logic](docs/platform-detection.md) for details.
- `scripts/validate_manifest.py` - Validates manifest structure and required fields
- `scripts/test_scripts.sh` - Test suite for the generation scripts

### Documentation
- `docs/platform-detection.md` - Platform detection algorithm and keyword mappings reference

### CI/CD
- `.github/workflows/update-manifest.yml` - Runs daily, on manual trigger, or when source files change. Regenerates and commits manifest.json automatically.

## Adding Content

**Binary package**: Add GitHub repo URL to `sources_repos.txt` (requires binary releases with platform-specific assets)

**Script**: Add Gist URL to `sources_scripts.txt` (supports .ps1, .sh, .bat, .cmd, .py extensions)
