# Unified workspace experiment

This is an experimental **multi-repository Gradle workspace** on the
`experiment/unified-workspace` branch. The five Java repositories remain
independent Git repositories; this repo pins them as **real Git submodules**.

## Get started

```powershell
git clone --branch experiment/unified-workspace --recurse-submodules https://github.com/NightWorldTeam/NWClient-DevTools.git NWClient-Workspace-Test
cd NWClient-Workspace-Test
```

The project's existing Gradle 8.10 wrapper is inside `Cosmetic`. Gradle finds
the root `settings.gradle` when launched from the workspace directory:

```powershell
.\Cosmetic\gradlew.bat -p . projects
.\Cosmetic\gradlew.bat -p . devClasses
.\Cosmetic\gradlew.bat -p . devBuild
```

`ReflectionTools` is included as a pinned Git submodule on its `main` branch.
It will be checked out together with the rest of the workspace.

## Repository pins

| Directory | Branch for explicit updates | Pinned commit |
| --- | --- | --- |
| Cosmetic | new-architecture | 16418d77cbf9c3bb75321720abb747a950ece50c |
| MinecraftApi | new-architecture | cb094de3532c636f542e93743908d10fcd9bc98e |
| MinecraftApi.Runtime | experiment/unified-workspace-compat | 1b9acde093164cc8b8ec12c1faf76f2557492dd3 |
| LaunchLinker | new-architecture | 3fbb477c08a37140986b3212646784e5db929341 |
| ReflectionTools | main | 9c2fa0ab48c3aacea24b352289d1269b2aaa8958 |

Submodules pin commits, **not moving branch tips**. Updates must be explicit:

```powershell
git submodule update --init --recursive
git submodule update --remote Cosmetic MinecraftApi MinecraftApi.Runtime LaunchLinker ReflectionTools
git add Cosmetic MinecraftApi MinecraftApi.Runtime LaunchLinker ReflectionTools
git commit -m "chore: update NWClient submodule pins"
```

## Vanilla development cycle

Run from the workspace root on Windows:

```powershell
git pull
git submodule update --init --recursive
.\Cosmetic\gradlew.bat -p . devPrepare
.\Cosmetic\gradlew.bat -p . devRun
# or, for an IDE remote Java debugger on localhost:5005
.\Cosmetic\gradlew.bat -p . devDebug
```

The Vanilla preparation tasks compile Java, package raw JARs, remap only the
Vanilla variant, append the member metadata, and stage five artifacts under
`build/dev-artifacts/`. These tasks are incremental within this workspace.

Before `devRun`, configure a **private, gitignored** `deploy.toml` with the
correct `target`, `java_home`, and `[launch].command`. The launch command
must reference the expected five staged JAR names in the classpath.
`nwclient_dev.py` will fail instead of silently deploying stale artifacts
if any filename is missing. It then copies only those five JARs to the
configured development installation and starts Minecraft with its local profile.

`devDebug` additionally opens the JDWP debugger on
`127.0.0.1:5005`. Attach the IDE's Remote JVM Debugger there.
The launcher command and any credentials are deliberately never printed or
written to a generated .cmd file. **Do not reuse credentials committed in
example files; use your own local development session.**

The current remapping converter and member tool are Windows executables;
`devPrepare` therefore requires Windows with their existing prerequisites
installed. A successful in-game launch has not yet been verified.

## Current scope

- `devClasses`: incrementally compile both Cosmetic and MinecraftApi.Runtime (plus dependencies), without intentionally invoking packaging/remapping. All Java compile tasks use UTF-8 in this workspace.
- `devBuild`: run the current module build tasks. These still include the
  child projects' Windows-only `postBuild` remapping, which is not optimized yet.
- `devPrepare`, `devRun` and `devDebug` now exist as experimental tasks. The
  existing `build.py` and `deploy.py` remain available but are not invoked
  by these tasks. XML Live Reload is not implemented yet.
- User testing identified Windows-1252 compiler errors and a missing Runtime scissor contract; the workspace now forces UTF-8 and pins a compatibility fix on `MinecraftApi.Runtime/experiment/unified-workspace-compat`. Verify with `devClasses --rerun-tasks`. The user has confirmed `devClasses --rerun-tasks` succeeded (10 tasks in 2s), but `devPrepare` and an actual Minecraft launch have not yet been verified.

Do not store Minecraft access tokens or expanded launch commands in committed
configuration, CI logs, or shared scripts.
