# Wenget Bucket

A curated collection of CLI tools and scripts for [Wenget](https://github.com/superyngo/Wenget).

## 📦 Usage

Add this bucket to Wenget:

```bash
wenget bucket add superyngo https://raw.githubusercontent.com/superyngo/wenget-bucket/main/manifest.json
```

## 🔍 Search and Install

```bash
# Search for packages and scripts
wenget search ripgrep

# Install packages
wenget add ripgrep fd bat

# Install scripts
wenget add rclonemm mini-nano
```

## 📊 Statistics

- **Total Packages**: 20+ binary packages
- **Total Scripts**: 5+ utility scripts
- **Platform Coverage**: Windows, Linux, macOS (x86_64, ARM64)
- **Auto-Update**: Automated via Wenget + GitHub Actions

## 📝 Package List

### Search & Find
- **ripgrep** - Fast grep alternative
- **fd** - Simple find alternative
- **fzf** - Fuzzy finder

### File Viewers
- **bat** - Cat with syntax highlighting
- **hexyl** - Command-line hex viewer

### Development Tools
- **uv** - Python package installer
- **deno** - JavaScript/TypeScript runtime
- **bun** - JavaScript runtime
- **gh** - GitHub CLI

### System Tools
- **bottom** - Cross-platform system monitor
- **rclone** - Cloud storage sync
- **podman** - Container runtime
- **scrcpy** - Android screen mirroring

### Utility Scripts
- **rclonemm** - Rclone management script (Bash/PowerShell)
- **mini-nano** - Terminal text editor (PowerShell)
- **better-rm** - Enhanced rm command (Bash)

## 🔧 Maintenance

This bucket is maintained using Wenget's built-in `bucket create` command.

### Generating the Manifest

The manifest is generated from two source files:
- **sources_repos.txt** - GitHub repository URLs for binary packages
- **sources_scripts.txt** - Gist URLs for scripts

```bash
# Generate manifest.json using wenget
wenget bucket create -r sources_repos.txt -s sources_scripts.txt -o manifest.json

# Or add direct URLs
wenget bucket create -d https://github.com/user/repo,https://gist.github.com/user/id
```

### Adding New Content

**To add a binary package:**
1. Add the GitHub repository URL to `sources_repos.txt`
2. Run `wenget bucket create` or trigger the GitHub Action

**To add scripts:**
1. Add the Gist URL to `sources_scripts.txt`
2. All scripts in the gist will be automatically extracted
3. Run `wenget bucket create` or trigger the GitHub Action

### Automated Updates

The manifest is automatically updated via GitHub Actions:
- **Weekly**: Every Monday at midnight UTC
- **On push**: When `sources_repos.txt` or `sources_scripts.txt` changes
- **Manual**: Via workflow dispatch

## 🤝 Contributing

To suggest new content:

**For binary packages:**
1. Open an issue with the GitHub repository URL
2. Ensure the package has binary releases
3. Verify it supports major platforms (Windows, Linux, macOS)

**For scripts:**
1. Open an issue with the Gist URL
2. Ensure scripts are well-documented
3. Specify the script type (PowerShell, Bash, Python, Batch)

## 📁 Repository Structure

```
wenget-bucket/
├── manifest.json           # Generated manifest (do not edit manually)
├── sources_repos.txt       # GitHub repo URLs for packages
├── sources_scripts.txt     # Gist URLs for scripts
├── wenget                  # Wenget binary (Linux x86_64)
├── archive/                # Archived legacy scripts
│   └── scripts/            # Old Python-based generator
└── .github/workflows/      # Automation
```

## 📄 License

This repository configuration is released under MIT License.

Individual packages have their own licenses - check each package's repository.

## 🔗 Links

- **Wenget**: https://github.com/superyngo/Wenget
- **Issues**: https://github.com/superyngo/wenget-bucket/issues
