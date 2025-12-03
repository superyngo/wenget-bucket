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

- **Total Packages**: 14 binary packages
- **Total Scripts**: 3 utility scripts
- **Platform Coverage**: Windows, Linux, macOS (x86_64, ARM64)
- **Auto-Update**: Automated via generation script

## 📝 Package List

### Search & Find
- **ripgrep** - Fast grep alternative
- **fd** - Simple find alternative

### File Viewers
- **bat** - Cat with syntax highlighting
- **hexyl** - Command-line hex viewer

### Development Tools
- **hyperfine** - Command-line benchmarking

### Git Tools
- **gitui** - Terminal UI for git

### Navigation
- **zoxide** - Smarter cd command

### System Monitoring
- **bottom** - Cross-platform system monitor

### Shell Enhancement
- **starship** - Cross-shell prompt

### Utility Scripts
- **rclonemm** - Rclone management script for mounting remote storage (Bash)
- **reformat-ventoy** - Disk reformatting with Ventoy partition support (Bash)
- **mini-nano** - Terminal-based text editor for PowerShell

## 🔧 Maintenance

This bucket is maintained using automated scripts:

### Generating the Manifest

The manifest is generated from two source files:
- **sources_repos.txt** - GitHub repository URLs for binary packages
- **sources_scripts.txt** - Gist URLs for scripts (automatically extracts all scripts from each gist)

```bash
# Generate manifest.json
python scripts/generate_manifest.py

# Or with custom source files
python scripts/generate_manifest.py sources_repos.txt -s sources_scripts.txt -o manifest.json
```

### Adding New Content

**To add a binary package:**
1. Add the GitHub repository URL to `sources_repos.txt`
2. Regenerate the manifest

**To add scripts:**
1. Add the Gist URL to `sources_scripts.txt`
2. All scripts in the gist will be automatically extracted
3. Regenerate the manifest

The script automatically:
- Fetches latest release information from GitHub
- Detects supported platforms
- Extracts scripts from Gists
- Generates properly formatted manifest.json

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

## 📄 License

This repository configuration is released under MIT License.

Individual packages have their own licenses - check each package's repository.

## 🔗 Links

- **Wenget**: https://github.com/superyngo/Wenget
- **Issues**: https://github.com/superyngo/wenget-bucket/issues
