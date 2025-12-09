#!/usr/bin/env python3
"""
Wenget Bucket Manifest Generator

Lightweight script to generate manifest.json from sources.txt
Fetches package information from GitHub API without installing Wenget
"""

import os
import sys
import json
import re
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Dict, List, Optional, Any

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration
GITHUB_API_BASE = "https://api.github.com"
RATE_LIMIT_DELAY = 1  # seconds between requests
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


class GitHubAPI:
    """Simple GitHub API client"""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    def _make_request(self, url: str) -> Dict[str, Any]:
        """Make HTTP request to GitHub API"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Wenget-Bucket-Generator/1.0",
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        req = Request(url, headers=headers)

        for attempt in range(MAX_RETRIES):
            try:
                with urlopen(req, timeout=30) as response:
                    # Update rate limit info
                    self.rate_limit_remaining = response.headers.get(
                        "X-RateLimit-Remaining"
                    )
                    self.rate_limit_reset = response.headers.get("X-RateLimit-Reset")

                    data = json.loads(response.read().decode("utf-8"))
                    return data

            except HTTPError as e:
                if e.code == 403:
                    # Check if it's actually rate limit or permission issue
                    error_body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
                    if 'rate limit' in error_body.lower() or self.rate_limit_remaining == '0':
                        print(f"⚠️  Rate limit exceeded. Remaining: {self.rate_limit_remaining}")
                        print(f"   Waiting {RETRY_DELAY}s before retry...")
                    else:
                        print(f"⚠️  Permission denied (403): {url}")
                        print(f"   This might be a private resource or authentication issue")

                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        raise
                elif e.code == 404:
                    raise ValueError(f"Repository not found: {url}")
                else:
                    print(f"❌ HTTP Error {e.code}: {e.reason}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        raise

            except URLError as e:
                print(f"❌ Network error: {e.reason}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise

        raise Exception(f"Failed after {MAX_RETRIES} attempts")

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        return self._make_request(url)

    def get_latest_release(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get latest release information"""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/latest"
        return self._make_request(url)

    def check_rate_limit(self):
        """Print rate limit status"""
        if self.rate_limit_remaining:
            print(f"ℹ️  Rate limit: {self.rate_limit_remaining} remaining")


class PlatformDetector:
    """
    Detect platform from release asset filename using 4-component keyword matching:
    1. Extension (required) - archive/executable file types
    2. Platform (required) - OS identification
    3. Architecture (optional) - CPU architecture with smart defaults
    4. Compiler/Toolchain (optional) - for priority selection
    """

    # === KEYWORD MAPPING DICTIONARIES ===

    # Valid archive/executable extensions (portable only, no installers)
    EXTENSIONS: set = {
        ".exe",
        ".zip", ".7z", ".rar",
        ".tar.gz", ".tgz",
        ".tar.xz", ".txz",
        ".tar.bz2", ".tbz2",
    }

    # Platform keyword -> normalized platform name
    PLATFORM_KEYWORDS: Dict[str, str] = {
        # Windows variants
        "win": "windows",
        "windows": "windows",
        "pc-windows": "windows",
        # Linux variants
        "linux": "linux",
        "unknown-linux": "linux",
        # macOS/Darwin variants (all normalize to "darwin")
        "darwin": "darwin",
        "macos": "darwin",
        "mac": "darwin",
        "osx": "darwin",
        "apple": "darwin",
        "apple-darwin": "darwin",
        # FreeBSD
        "freebsd": "freebsd",
    }

    # Architecture keyword -> normalized architecture
    ARCH_KEYWORDS: Dict[str, str] = {
        # 64-bit x86 (longer matches first when sorted)
        "x86_64": "x86_64",
        "x86-64": "x86_64",
        "amd64": "x86_64",
        "x64": "x86_64",
        "win64": "x86_64",
        # 32-bit x86
        "i686": "i686",
        "i386": "i686",
        "win32": "i686",
        # ARM 64-bit
        "aarch64": "aarch64",
        "arm64": "aarch64",
        # ARM 32-bit v7
        "armv7": "armv7",
        "armhf": "armv7",
        "armv7l": "armv7",
        # ARM 32-bit v6
        "armv6": "armv6",
        # Generic ARM (assume v6)
        "arm": "armv6",
        # Note: "x86" alone is ambiguous, handle in _extract_architecture
    }

    # Architectures to skip (uncommon platforms we don't support)
    SKIP_ARCH_PATTERNS: set = {
        "s390x",  # IBM mainframe
        "ppc64",  # PowerPC 64-bit
        "ppc64le",  # PowerPC 64-bit LE
        "riscv64",  # RISC-V 64-bit
        "mips",  # MIPS
        "mipsel",  # MIPS little-endian
    }

    # Known compiler/toolchain keywords
    COMPILER_KEYWORDS: set = {
        "gnu",
        "musl",
        "msvc",
        "gnueabihf",
        "musleabihf",
        "musleabi",
    }

    # Compiler priority per platform (higher = preferred)
    COMPILER_PRIORITY: Dict[str, Dict[str, int]] = {
        "linux": {
            "musl": 3,
            "musleabihf": 3,
            "musleabi": 3,
            "gnu": 2,
            "gnueabihf": 2,
            "": 1,  # No compiler specified
        },
        "windows": {
            "msvc": 3,
            "gnu": 2,
            "musl": 1,
            "": 1,
        },
        "darwin": {"": 1},
        "freebsd": {"": 1},
    }

    # Default architecture when not specified in filename
    ARCH_DEFAULTS: Dict[str, Optional[str]] = {
        "windows": "x86_64",
        "linux": "x86_64",
        "darwin": None,  # Don't assume for Darwin - use whatever is available
        "freebsd": "x86_64",
    }

    # === EXTRACTION METHODS ===

    @classmethod
    def _extract_extension(cls, filename: str) -> Optional[str]:
        """Extract archive/executable extension from filename."""
        filename_lower = filename.lower()
        # Check compound extensions first (longer ones take priority)
        for ext in sorted(cls.EXTENSIONS, key=len, reverse=True):
            if filename_lower.endswith(ext):
                return ext
        return None

    @classmethod
    def _extract_platform(cls, filename: str, extension: str) -> Optional[str]:
        """
        Extract and normalize platform from filename.
        Returns: normalized platform name or None if not detected
        """
        filename_lower = filename.lower()

        # Special case: .exe implies Windows
        if extension == ".exe":
            # Still check for explicit platform markers first
            for keyword in sorted(cls.PLATFORM_KEYWORDS.keys(), key=len, reverse=True):
                if keyword in filename_lower:
                    return cls.PLATFORM_KEYWORDS[keyword]
            return "windows"  # Default for .exe

        # Check platform keywords (longer matches first for specificity)
        for keyword in sorted(cls.PLATFORM_KEYWORDS.keys(), key=len, reverse=True):
            if keyword in filename_lower:
                return cls.PLATFORM_KEYWORDS[keyword]

        # No platform found - skip this file
        return None

    @classmethod
    def _extract_architecture(cls, filename: str, platform: Optional[str] = None) -> Optional[str]:
        """
        Extract and normalize architecture from filename.

        Args:
            filename: The asset filename
            platform: The detected platform (used for context-aware decisions)

        Returns:
            - Normalized architecture string
            - "SKIP" if the architecture should be skipped
            - None if no architecture detected
        """
        filename_lower = filename.lower()

        # Check for architectures we want to skip
        for skip_arch in cls.SKIP_ARCH_PATTERNS:
            if skip_arch in filename_lower:
                return "SKIP"

        # Check architecture keywords (longer matches first)
        for keyword in sorted(cls.ARCH_KEYWORDS.keys(), key=len, reverse=True):
            if keyword in filename_lower:
                return cls.ARCH_KEYWORDS[keyword]

        # Special handling for ambiguous "x86" (could be 32 or 64-bit)
        # If "x86" appears but not "x86_64" or "x86-64"
        if "x86" in filename_lower and "x86_64" not in filename_lower and "x86-64" not in filename_lower:
            # For Darwin, "x86" means x86_64 (32-bit Mac hasn't been supported since 10.15)
            if platform == "darwin":
                return "x86_64"
            # For other platforms, "x86" typically means 32-bit
            return "i686"

        return None

    @classmethod
    def _extract_compiler(cls, filename: str) -> str:
        """Extract compiler/toolchain from filename."""
        filename_lower = filename.lower()
        for compiler in cls.COMPILER_KEYWORDS:
            if compiler in filename_lower:
                return compiler
        return ""

    # === MAIN DETECTION METHODS ===

    @classmethod
    def detect_platform(cls, filename: str) -> Optional[str]:
        """
        Detect platform from filename using 4-component keyword matching.

        Returns:
            - "{platform}-{arch}" normalized platform key
            - "{platform}" if arch cannot be determined (e.g., darwin without arch)
            - None if not a valid archive/executable or should be skipped
        """
        # Step 1: Check extension (required)
        extension = cls._extract_extension(filename)
        if extension is None:
            return None

        # Step 2: Extract platform
        platform = cls._extract_platform(filename, extension)

        # Step 3: Skip if no platform detected
        if platform is None:
            return None

        # Step 4: Extract architecture (pass platform for context-aware decisions)
        arch = cls._extract_architecture(filename, platform)

        # Step 4.5: Skip unsupported architectures
        if arch == "SKIP":
            return None

        # Step 5: Apply defaults if no arch found
        if arch is None:
            arch = cls.ARCH_DEFAULTS.get(platform)

        # Step 6: Build platform key
        if arch:
            return f"{platform}-{arch}"
        else:
            # Edge case: platform without arch (e.g., darwin without explicit arch)
            print(f"   ⚠️  No architecture detected: {filename} -> {platform}")
            return platform

    @classmethod
    def get_asset_priority(cls, filename: str, platform_key: str) -> int:
        """
        Get priority for asset selection when multiple assets exist
        for the same platform-arch combination.

        Higher priority = preferred.
        Used for: Linux (musl > gnu), Windows (msvc > gnu > musl)
        """
        compiler = cls._extract_compiler(filename)

        # Extract base platform from platform_key
        platform = platform_key.split("-")[0] if "-" in platform_key else platform_key

        # Get priority from configuration
        platform_priorities = cls.COMPILER_PRIORITY.get(platform, {"": 1})
        return platform_priorities.get(compiler, 1)


class ManifestGenerator:
    """Generate manifest.json from sources.txt"""

    def __init__(self, github_token: Optional[str] = None):
        self.api = GitHubAPI(github_token)
        self.packages = []
        self.scripts = []

    def parse_github_url(self, url: str) -> Optional[tuple]:
        """Parse GitHub URL to extract owner and repo"""
        patterns = [
            r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$",
            r"github\.com/([^/]+)/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)

        return None

    def parse_gist_url(self, url: str) -> Optional[str]:
        """Parse Gist URL to extract gist ID"""
        patterns = [
            r"gist\.github\.com/[^/]+/([a-f0-9]+)",
            r"gist\.githubusercontent\.com/[^/]+/([a-f0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def is_raw_script_url(self, url: str) -> bool:
        """Check if URL is a raw script URL (e.g., raw.githubusercontent.com)"""
        url_lower = url.lower()
        # Support raw.githubusercontent.com and other direct raw URLs
        return "raw.githubusercontent.com" in url_lower or url_lower.startswith("https://raw.")

    def detect_script_type(self, filename: str) -> Optional[str]:
        """Detect script type from filename extension"""
        ext_map = {
            ".ps1": "powershell",
            ".sh": "bash",
            ".bat": "batch",
            ".cmd": "batch",
            ".py": "python",
        }

        for ext, script_type in ext_map.items():
            if filename.lower().endswith(ext):
                return script_type

        return None

    def detect_script_type_from_shebang(self, content: str) -> Optional[str]:
        """Detect script type from shebang line"""
        if not content:
            return None

        # Get first line
        first_line = content.split('\n')[0].strip()

        if not first_line.startswith('#!'):
            return None

        # Map shebang to script type
        shebang_lower = first_line.lower()
        if 'bash' in shebang_lower or 'sh' in shebang_lower:
            return 'bash'
        elif 'python' in shebang_lower:
            return 'python'
        elif 'pwsh' in shebang_lower or 'powershell' in shebang_lower:
            return 'powershell'

        return None

    def fetch_raw_script(self, url: str) -> List[Dict[str, Any]]:
        """Fetch script information from a raw script URL"""
        try:
            # Extract filename from URL
            filename = url.rstrip("/").split("/")[-1]

            # Detect script type from filename first
            script_type = self.detect_script_type(filename)

            # If no extension, try to fetch content and check shebang
            if not script_type:
                print(f"   ℹ️  No extension detected, checking shebang for: {filename}")
                try:
                    headers = {
                        "User-Agent": "Wenget-Bucket-Generator/1.0",
                    }
                    req = Request(url, headers=headers)
                    with urlopen(req, timeout=30) as response:
                        # Only read first 1KB to check shebang
                        content = response.read(1024).decode('utf-8', errors='ignore')
                        script_type = self.detect_script_type_from_shebang(content)

                    if script_type:
                        print(f"   ✓ Detected {script_type} from shebang")
                    else:
                        print(f"   ⚠️  Cannot detect script type from shebang")
                        return []
                except Exception as e:
                    print(f"   ⚠️  Failed to fetch content for shebang detection: {e}")
                    return []

            # Remove extension from script name
            name = filename
            for ext in [".ps1", ".sh", ".bat", ".cmd", ".py"]:
                if name.endswith(ext):
                    name = name[:-len(ext)]
                    break

            # Try to extract repo URL from raw URL
            # Example: https://raw.githubusercontent.com/owner/repo/refs/heads/main/file
            # -> https://github.com/owner/repo
            repo_url = None
            github_match = re.search(r"raw\.githubusercontent\.com/([^/]+)/([^/]+)", url)
            if github_match:
                owner, repo = github_match.groups()
                repo_url = f"https://github.com/{owner}/{repo}"

            script = {
                "name": name,
                "description": f"{filename} from {repo_url or url}",
                "url": url,
                "script_type": script_type,
                "repo": repo_url or url,
            }

            return [script]

        except Exception as e:
            print(f"❌ Error processing raw script {url}: {e}")
            return []

    def fetch_gist_scripts(self, url: str) -> List[Dict[str, Any]]:
        """Fetch script information from GitHub Gist"""
        gist_id = self.parse_gist_url(url)
        if not gist_id:
            print(f"⚠️  Invalid Gist URL: {url}")
            return []

        try:
            # Get gist info (use anonymous access for public gists)
            gist_url = f"{GITHUB_API_BASE}/gists/{gist_id}"

            # Create a temporary API client without token for gist access
            # GITHUB_TOKEN from Actions doesn't have permission to access gists
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Wenget-Bucket-Generator/1.0",
            }
            req = Request(gist_url, headers=headers)

            with urlopen(req, timeout=30) as response:
                gist_data = json.loads(response.read().decode("utf-8"))

            scripts = []
            files = gist_data.get("files", {})

            for filename, file_info in files.items():
                script_type = self.detect_script_type(filename)
                if not script_type:
                    print(f"   ⚠️  Skipping non-script file: {filename}")
                    continue

                # Remove extension from script name
                name = filename
                for ext in [".ps1", ".sh", ".bat", ".cmd", ".py"]:
                    if name.endswith(ext):
                        name = name[:-len(ext)]
                        break

                script = {
                    "name": name,
                    "description": gist_data.get("description") or f"{filename} from gist",
                    "url": file_info["raw_url"],
                    "script_type": script_type,
                    "repo": gist_data["html_url"],
                }

                scripts.append(script)

            return scripts

        except Exception as e:
            print(f"❌ Error fetching gist {gist_id}: {e}")
            return []

    def fetch_scripts_from_url(self, url: str) -> List[Dict[str, Any]]:
        """Fetch scripts from URL - supports both Gist and raw script URLs"""
        # Check if this is a raw script URL
        if self.is_raw_script_url(url):
            return self.fetch_raw_script(url)
        # Otherwise treat as Gist URL
        else:
            return self.fetch_gist_scripts(url)

    def fetch_package_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from GitHub"""
        parsed = self.parse_github_url(url)
        if not parsed:
            print(f"⚠️  Invalid GitHub URL: {url}")
            return None

        owner, repo = parsed

        try:
            # Get repository info
            repo_info = self.api.get_repo_info(owner, repo)

            # Get latest release
            try:
                release = self.api.get_latest_release(owner, repo)
            except Exception as e:
                print(f"⚠️  No releases found for {owner}/{repo}: {e}")
                return None

            # Extract platform binaries from assets
            # Track platform info with priority for compiler variants
            platforms = {}
            platform_priorities = {}  # Track priority of selected assets

            for asset in release.get("assets", []):
                platform = PlatformDetector.detect_platform(asset["name"])
                if platform:
                    asset_info = {
                        "url": asset["browser_download_url"],
                        "size": asset["size"],
                    }

                    # Get priority for this asset (supports all platforms)
                    # Linux: musl > gnu, Windows: msvc > gnu > musl
                    current_priority = PlatformDetector.get_asset_priority(asset["name"], platform)
                    existing_priority = platform_priorities.get(platform, 0)

                    # Only update if current asset has higher priority
                    if current_priority > existing_priority:
                        platforms[platform] = asset_info
                        platform_priorities[platform] = current_priority

            if not platforms:
                print(f"⚠️  No binary assets found for {owner}/{repo}")
                return None

            # Build package info
            package = {
                "name": repo_info["name"],
                "description": repo_info["description"] or "",
                "repo": repo_info["html_url"],
                "homepage": repo_info["homepage"],
                "license": repo_info["license"]["spdx_id"]
                if repo_info.get("license")
                else None,
                "platforms": platforms,
            }

            return package

        except Exception as e:
            print(f"❌ Error fetching {owner}/{repo}: {e}")
            return None

    def load_sources(self, sources_file: str) -> List[str]:
        """Load GitHub URLs from sources file"""
        urls = []

        if not sources_file or not os.path.exists(sources_file):
            return urls

        with open(sources_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    urls.append(line)

        return urls

    def generate(self, sources_file: str, sources_scripts_file: str, output_file: str):
        """Generate manifest.json from sources files"""
        print("🚀 Wenget Bucket Manifest Generator")
        print("=" * 50)

        # Load script sources FIRST (to avoid rate limit issues)
        print(f"\n📖 Loading script sources from {sources_scripts_file}...")
        gist_urls = self.load_sources(sources_scripts_file)
        print(f"✓ Found {len(gist_urls)} gists")

        # Fetch script info FIRST
        if gist_urls:
            print(f"\n📜 Fetching script information...")
            for i, url in enumerate(gist_urls, 1):
                print(f"\n[{i}/{len(gist_urls)}] {url}")

                scripts = self.fetch_scripts_from_url(url)
                if scripts:
                    self.scripts.extend(scripts)
                    for script in scripts:
                        print(f"   ✓ {script['name']} ({script['script_type']})")

                # Rate limiting
                if i < len(gist_urls):
                    time.sleep(RATE_LIMIT_DELAY)

                # Show rate limit status periodically
                if i % 10 == 0:
                    self.api.check_rate_limit()

        # Load package sources AFTER scripts
        print(f"\n📖 Loading package sources from {sources_file}...")
        urls = self.load_sources(sources_file)
        print(f"✓ Found {len(urls)} repositories")

        # Fetch package info
        print(f"\n📦 Fetching package information...")
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")

            package = self.fetch_package_info(url)
            if package:
                self.packages.append(package)
                print(f"   ✓ {package['name']} - {len(package['platforms'])} platforms")

            # Rate limiting
            if i < len(urls):
                time.sleep(RATE_LIMIT_DELAY)

            # Show rate limit status periodically
            if i % 10 == 0:
                self.api.check_rate_limit()

        # Save manifest
        print(f"\n💾 Saving manifest to {output_file}...")
        manifest_obj = {
            "packages": self.packages,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Add scripts if any
        if self.scripts:
            manifest_obj["scripts"] = self.scripts

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(manifest_obj, f, indent=2, ensure_ascii=False)

        # Summary
        print("\n" + "=" * 50)
        print("✅ Generation complete!")
        print(f"   Total packages: {len(self.packages)}/{len(urls)}")
        print(f"   Total scripts: {len(self.scripts)}")
        print(f"   Output file: {output_file}")

        # Platform statistics
        platform_stats = {}
        for pkg in self.packages:
            for platform in pkg["platforms"].keys():
                platform_stats[platform] = platform_stats.get(platform, 0) + 1

        if platform_stats:
            print("\n📊 Platform coverage:")
            for platform, count in sorted(platform_stats.items()):
                print(f"   {platform}: {count} packages")

        # Script type statistics
        if self.scripts:
            script_type_stats = {}
            for script in self.scripts:
                script_type = script["script_type"]
                script_type_stats[script_type] = script_type_stats.get(script_type, 0) + 1

            print("\n📜 Script types:")
            for script_type, count in sorted(script_type_stats.items()):
                print(f"   {script_type}: {count} scripts")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Wenget bucket manifest from sources"
    )
    parser.add_argument(
        "sources",
        nargs="?",
        default="sources_repos.txt",
        help="Source file containing GitHub repository URLs (default: sources_repos.txt)",
    )
    parser.add_argument(
        "-s",
        "--scripts",
        default="sources_scripts.txt",
        help="Source file containing Gist URLs for scripts (default: sources_scripts.txt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="manifest.json",
        help="Output manifest file (default: manifest.json)",
    )
    parser.add_argument(
        "-t",
        "--token",
        help="GitHub personal access token (or use GITHUB_TOKEN env var)",
    )

    args = parser.parse_args()

    # Check if sources file exists
    if not os.path.exists(args.sources):
        print(f"❌ Error: Source file '{args.sources}' not found")
        sys.exit(1)

    # Generate manifest
    try:
        generator = ManifestGenerator(args.token)
        generator.generate(args.sources, args.scripts, args.output)
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
