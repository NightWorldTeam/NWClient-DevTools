# Unified workspace experiment

This is an experimental **multi-repository Gradle workspace** on the
`experiment/unified-workspace` branch. The four Java repositories remain
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

A local checkout of `ReflectionTools` is additionally necessary for the
current `project(":ReflectionTools")` dependencies. Its source repository is
not yet available through the GitHub connection and is **not** represented by a
fabricated gitlink. Place the checkout in `ReflectionTools/`, or migrate those
dependencies to a published and version-pinned artifact.

## Repository pins

| Directory | Branch for explicit updates | Pinned commit |
| --- | --- | --- |
| Cosmetic | new-architecture | 16418d77cbf9c3bb75321720abb747a950ece50c |
| MinecraftApi | new-architecture | cb094de3532c636f542e93743908d10fcd9bc98e |
| MinecraftApi.Runtime | main | 4cfb74010aaa92e64b45a5657d5602c03f22c0aa |
| LaunchLinker | new-architecture | 3fbb477c08a37140986b3212646784e5db929341 |

Submodules pin commits, **not moving branch tips**. Updates must be explicit:

```powershell
git submodule update --init --recursive
git submodule update --remote Cosmetic MinecraftApi MinecraftApi.Runtime LaunchLinker
git add Cosmetic MinecraftApi MinecraftApi.Runtime LaunchLinker
git commit -m "chore: update NWClient submodule pins"
```

## Current scope

- `devClasses`: compile existing Gradle projects incrementally, without intentionally invoking packaging/remapping.
- `devBuild`: run the current module build tasks. These still include the
  child projects' Windows-only `postBuild` remapping, which is not optimized yet.
- Minecraft launch, deploy, debugger, and Live Reload are **not** integrated into
  the new Gradle workspace yet. The pre-existing `build.py` and `deploy.py`
  remain available, but they predate this root multi-project build.
- No builds or Minecraft launches have been tested in this branch.

Do not store Minecraft access tokens or expanded launch commands in committed
configuration, CI logs, or shared scripts.
