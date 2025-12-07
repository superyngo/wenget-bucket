# Platform Detection Logic

本文件說明 `generate_manifest.py` 中 `PlatformDetector` 類別的平台偵測邏輯，可供其他專案參考使用。

## 概述

從 GitHub Release 的 asset 檔名中解析出平台資訊，使用 **4 要件關鍵字比對**：

1. **副檔名** (Extension) - 必要
2. **平台** (Platform) - 必要
3. **架構** (Architecture) - 選填，有智慧預設
4. **編譯器** (Compiler) - 選填，用於優先序選擇

## 偵測流程

```
detect_platform(filename)
│
├─ 1. 提取副檔名
│     └─ 無效副檔名 → return None (跳過)
│
├─ 2. 提取平台
│     ├─ .exe 隱含 Windows
│     └─ 無平台關鍵字 → return None (跳過)
│
├─ 3. 提取架構
│     ├─ 檢查跳過清單 (s390x, ppc64...) → return None
│     ├─ Mac 上的 "x86" → x86_64 (特殊處理)
│     └─ 其他平台 "x86" → i686
│
├─ 4. 套用預設架構
│     ├─ Windows → x86_64
│     ├─ Linux → x86_64
│     ├─ Darwin → None (不預設)
│     └─ FreeBSD → x86_64
│
└─ 5. 組合結果
      ├─ 有架構 → "{platform}-{arch}"
      └─ 無架構 → "{platform}"
```

## 關鍵字映射

### 副檔名 (EXTENSIONS)

僅處理 portable 檔案，不含安裝程式：

```python
EXTENSIONS = {
    ".exe",
    ".zip", ".7z", ".rar",
    ".tar.gz", ".tgz",
    ".tar.xz", ".txz",
    ".tar.bz2", ".tbz2",
}
```

### 平台關鍵字 (PLATFORM_KEYWORDS)

| 關鍵字 | 歸一化為 |
|--------|----------|
| `win`, `windows`, `pc-windows` | `windows` |
| `linux`, `unknown-linux` | `linux` |
| `darwin`, `macos`, `mac`, `osx`, `apple`, `apple-darwin` | `darwin` |
| `freebsd` | `freebsd` |

### 架構關鍵字 (ARCH_KEYWORDS)

| 關鍵字 | 歸一化為 | 說明 |
|--------|----------|------|
| `x86_64`, `x86-64`, `amd64`, `x64`, `win64` | `x86_64` | 64-bit x86 |
| `i686`, `i386`, `win32` | `i686` | 32-bit x86 |
| `aarch64`, `arm64` | `aarch64` | 64-bit ARM |
| `armv7`, `armhf`, `armv7l` | `armv7` | 32-bit ARM v7 |
| `armv6` | `armv6` | 32-bit ARM v6 |
| `arm` | `armv6` | 通用 ARM (假設 v6) |

**特殊處理**：單獨的 `x86` 關鍵字
- Darwin 平台：視為 `x86_64`（32-bit Mac 已不支援）
- 其他平台：視為 `i686`

### 跳過的架構 (SKIP_ARCH_PATTERNS)

這些架構會被直接跳過：

```python
SKIP_ARCH_PATTERNS = {
    "s390x",    # IBM mainframe
    "ppc64",    # PowerPC 64-bit
    "ppc64le",  # PowerPC 64-bit LE
    "riscv64",  # RISC-V 64-bit
    "mips",     # MIPS
    "mipsel",   # MIPS little-endian
}
```

### 編譯器關鍵字 (COMPILER_KEYWORDS)

```python
COMPILER_KEYWORDS = {
    "gnu", "musl", "msvc",
    "gnueabihf", "musleabihf", "musleabi",
}
```

## 優先序選擇

當同一平台-架構有多個 assets 時，依編譯器優先序選擇：

### Linux 優先序

```
musl (3) > gnu (2) > 無標記 (1)
```

- `musl`: 靜態連結，無依賴，適合 portable
- `gnu`: 動態連結 glibc

### Windows 優先序

```
msvc (3) > gnu (2) > musl (1)
```

- `msvc`: 原生 Windows 編譯
- `gnu`: MinGW 編譯

### Darwin / FreeBSD

通常沒有編譯器變體，優先序均為 1。

## 範例

| 檔名 | 結果 | 說明 |
|------|------|------|
| `ripgrep-x86_64-pc-windows-msvc.zip` | `windows-x86_64` (p:3) | msvc 優先 |
| `ripgrep-x86_64-pc-windows-gnu.zip` | `windows-x86_64` (p:2) | gnu 次之 |
| `ripgrep-x86_64-unknown-linux-musl.tar.gz` | `linux-x86_64` (p:3) | musl 優先 |
| `ripgrep-x86_64-unknown-linux-gnu.tar.gz` | `linux-x86_64` (p:2) | gnu 次之 |
| `ripgrep-aarch64-apple-darwin.tar.gz` | `darwin-aarch64` (p:1) | Apple Silicon |
| `gitui-mac.tar.gz` | `darwin` | 無架構，不預設 |
| `gitui-mac-x86.tar.gz` | `darwin-x86_64` | Mac x86 = x86_64 |
| `gitui-win.tar.gz` | `windows-x86_64` | 預設 x86_64 |
| `gitui-linux.tar.gz` | `linux-x86_64` | 預設 x86_64 |
| `tool.exe` | `windows-x86_64` | .exe 隱含 Windows |
| `choco.zip` | `None` (跳過) | 無平台資訊 |
| `ripgrep-s390x-linux.tar.gz` | `None` (跳過) | 不支援的架構 |

## 程式碼結構

```python
class PlatformDetector:
    # 關鍵字字典
    EXTENSIONS: set
    PLATFORM_KEYWORDS: Dict[str, str]
    ARCH_KEYWORDS: Dict[str, str]
    SKIP_ARCH_PATTERNS: set
    COMPILER_KEYWORDS: set
    COMPILER_PRIORITY: Dict[str, Dict[str, int]]
    ARCH_DEFAULTS: Dict[str, Optional[str]]

    # 提取方法
    @classmethod
    def _extract_extension(cls, filename: str) -> Optional[str]

    @classmethod
    def _extract_platform(cls, filename: str, extension: str) -> Optional[str]

    @classmethod
    def _extract_architecture(cls, filename: str, platform: Optional[str]) -> Optional[str]

    @classmethod
    def _extract_compiler(cls, filename: str) -> str

    # 主要方法
    @classmethod
    def detect_platform(cls, filename: str) -> Optional[str]

    @classmethod
    def get_asset_priority(cls, filename: str, platform_key: str) -> int
```

## 使用範例

```python
from generate_manifest import PlatformDetector

# 偵測平台
platform = PlatformDetector.detect_platform("ripgrep-x86_64-unknown-linux-musl.tar.gz")
# 結果: "linux-x86_64"

# 取得優先序
priority = PlatformDetector.get_asset_priority(filename, platform)
# 結果: 3 (musl)

# 在多個 assets 中選擇最佳版本
assets = [...]
best_assets = {}
priorities = {}

for asset in assets:
    platform = PlatformDetector.detect_platform(asset["name"])
    if platform:
        priority = PlatformDetector.get_asset_priority(asset["name"], platform)
        if priority > priorities.get(platform, 0):
            best_assets[platform] = asset
            priorities[platform] = priority
```

## 擴展指南

### 新增平台支援

在 `PLATFORM_KEYWORDS` 加入新的關鍵字映射：

```python
PLATFORM_KEYWORDS["netbsd"] = "netbsd"
```

### 新增架構支援

在 `ARCH_KEYWORDS` 加入新的關鍵字映射：

```python
ARCH_KEYWORDS["loongarch64"] = "loongarch64"
```

### 調整編譯器優先序

修改 `COMPILER_PRIORITY` 字典：

```python
COMPILER_PRIORITY["linux"]["musl"] = 2  # 降低 musl 優先序
COMPILER_PRIORITY["linux"]["gnu"] = 3   # 提高 gnu 優先序
```
