# NWClient Build & Deploy

Automated tools for building NightWorld libraries (NWClient) and deploying the output JARs to your Minecraft development environment.

## Quick start

```bash
# Build Cosmetic (top-level project, includes all deps) and deploy
python build.py

# Deploy only (after manual build)
python deploy.py

# Preview what would be copied
python deploy.py --dry-run
```

## Files

| File | Purpose |
|---|---|
| `deploy.toml` | Configuration: target path + JAR copy rules |
| `deploy.py` | Copies built JARs to the configured target directory |
| `build.py` | Runs Gradle build + deploy + optionally launch in one step |

## Configuration

Edit `deploy.toml` to set your Minecraft libraries path:

```toml
target = ".lexplosion/libraries/org/nightworld"
```

You can use environment variables in the path:

```toml
target = "%APPDATA%/.lexplosion/libraries/org/nightworld"   # Windows
target = "$HOME/.lexplosion/libraries/org/nightworld"        # Linux / macOS
```

Relative paths are resolved from the workspace root (where `deploy.toml` lives).

### JAR mappings

Each project section maps glob patterns to destination subdirectories:

```toml
[projects.Cosmetic]
"build/libs/*.jar" = "Cosmetics/1.0/"
"build/out/*.jar" = "Cosmetics/1.0/"
```

- The key is a glob pattern relative to the project root (e.g. `build/libs/*.jar`)
- The value is the destination **subdirectory** under `target`
- Projects with dots in their name must be quoted: `[projects."MinecraftApi.Runtime"]`
- All JAR variants (vanilla, forge, fabric, raw) within a project go to the same version folder

### Target directory structure

After deploy, the target directory will look like:

```
{target}/
├── Cosmetics/
│   └── 1.0/
│       ├── Cosmetics-1.20-1.0.jar
│       ├── Cosmetics-fabric-1.20-1.0.jar
│       ├── Cosmetics-forge-1.20-1.0.jar
│       └── Cosmetics-vanilla-1.20-1.0.jar
├── LaunchLinker/
│   └── 1.0/
│       └── LaunchLinker-1.0.jar
├── MinecraftApi/
│   └── 1.0/
│       ├── MinecraftApi-1.20-1.0.jar
│       ├── MinecraftApi-fabric-1.20-1.0.jar
│       ├── MinecraftApi-forge-1.20-1.0.jar
│       └── MinecraftApi-vanilla-1.20-1.0.jar
├── MinecraftApi.Runtime/
│   └── 1.0/
│       ├── MinecraftApi.Runtime-1.20-1.0.jar
│       ├── MinecraftApi.Runtime-fabric-1.20-1.0.jar
│       └── MinecraftApi.Runtime-vanilla-1.20-1.0.jar
└── ReflectionTools/
    └── 1.0/
        └── ReflectionTools-1.0.jar
```

## Usage

### `build.py` — build + deploy

```bash
# Build Cosmetic (default) and deploy
python build.py

# Build a specific project and deploy
python build.py MinecraftApi

# Build multiple projects
python build.py MinecraftApi MinecraftApi.Runtime

# Build all 5 projects in dependency order
python build.py --all

# Build only, skip deploy
python build.py --no-deploy

# Preview deploy (dry-run) after building
python build.py --dry-run

# Include postBuild remapping (Windows only)
python build.py --remap

# Use a portable JDK from a folder (no system install needed)
python build.py --java-home D:/portable/jdk-17

# Build + deploy + launch the game
python build.py --launch

# Launch the game directly (skip build + deploy)
python build.py --launch-only
```

### `deploy.py` — deploy only

```bash
# Copy all matched JARs to target
python deploy.py

# Preview only
python deploy.py --dry-run

# Minimal output
python deploy.py --quiet
```

## Workflows

### Daily development (Windows)

```bash
# Build + deploy with remapping (produces remapped JARs in mods/)
python build.py --remap
```

### Daily development (Linux / macOS)

```bash
# Build + deploy (remapping.bat requires cmd.exe, skipped automatically)
python build.py
```

### Build a specific library

```bash
python build.py MinecraftApi
python deploy.py --dry-run  # verify mappings
python deploy.py            # copy to target
```

### Full rebuild of everything

```bash
python build.py --all
```

## Cross-platform notes

| Platform | `build.py` behavior | `deploy.py` behavior |
|---|---|---|
| **Windows** | Runs `./gradlew build` including `postBuild` (remapping) | Works natively |
| **Linux** | Runs `./gradlew build -x postBuild` (skips Windows-only remapping) | Works natively |
| **macOS** | Same as Linux | Works natively |

The `postBuild` task runs `remapping.bat` via `cmd.exe`, which only exists on Windows. On Linux/macOS, `build.py` automatically skips it with `-x postBuild`. The raw compiled JARs in `build/libs/` are still produced and deployed.

To run remapping on non-Windows, you would need to port `remapping.bat` to a shell script — that's outside the scope of this tool.

## Portable JDK (no system install)

If you don't want to install Java system-wide, use a portable JDK:

1. Download a JDK 17 archive (e.g. from [Adoptium](https://adoptium.net)) and extract it to any folder
2. Point to it with `--java-home`:

```bash
python build.py --java-home D:/portable/jdk-17.0.12
```

You can also set the `JAVA_HOME` environment variable once in your terminal instead of passing `--java-home` every time:

```bash
set JAVA_HOME=D:/portable/jdk-17.0.12    # Windows cmd
$env:JAVA_HOME="D:/portable/jdk-17.0.12" # PowerShell
python build.py
```

## Launch configuration

The `[launch]` section in `deploy.toml` defines the Minecraft launch command. It uses these template variables:

| Variable | Resolves to |
|---|---|
| `{java}` | Java executable from `--java-home` or `JAVA_HOME` |
| `{target}` | The deploy target directory |
| `{libraries}` | Parent of `target` (the `libraries/` base) |
| `{root}` | Parent of `libraries` (the `.lexplosion/` root) |
| `{cpsep}` | Classpath separator (`;` on Windows, `:` on Linux/macOS) |
| `${VAR}` or `%VAR%` | Environment variable expansion |

To update the command, edit the `command` value in `deploy.toml` under `[launch]`.

## How it works

1. `build.py` runs `./gradlew build` (with or without `postBuild`) in each requested project
2. After all builds succeed, it calls `deploy.py`
3. `deploy.py` reads `deploy.toml`, expands glob patterns per project, and copies matched files to `target`
4. If `--launch` is set, `build.py` reads the `[launch]` command from `deploy.toml`, substitutes variables, and runs it
5. If a project hasn't been built yet (no matching files), it's silently skipped

## Adding a new project

1. Add its name to the `PROJECTS` list in `build.py`
2. Add a section to `deploy.toml` with its JAR mappings
3. Done — `python build.py --all` will pick it up

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `deploy.py` says "no files matching" | Project hasn't been built yet | Run `python build.py <project>` first |
| `'target' not set` | Missing or misconfigured `deploy.toml` | Check the `target` field |
| `build.py` says "no gradlew script" | Gradle wrapper not generated | Run `gradle wrapper` in the project dir |
| Remapped JARs missing on Linux | `postBuild` is Windows-only | Use raw JARs from `build/libs/` or port `remapping.bat` |
| `tomllib` import error | Python < 3.11 | Run `pip install tomli` or upgrade Python |
| `JAVA_HOME not set` | No JDK installed/found | Use `--java-home D:/path/to/jdk` with a portable JDK folder |
| Launch says "no Java" | `--java-home` missing or wrong path | Pass correct `--java-home` (JDK root, bin/, or java.exe) |
| Launch command broken | Classpath needs updating | Edit the `command` in `deploy.toml`'s `[launch]` section |
