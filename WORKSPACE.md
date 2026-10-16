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

## Plug-and-play Windows development

The default tasks are intentionally **configuration-free**:

\`\`\`powershell
git pull
git submodule update --init --recursive
.\Cosmetic\gradlew.bat -p . devCheck
.\Cosmetic\gradlew.bat -p . devRun
# Or run with JDWP remote debugger on 127.0.0.1:5005:
.\Cosmetic\gradlew.bat -p . devDebug
\`\`\`

- Launcher root: \`%APPDATA%/.lexplosion\`
- Libraries: \`%APPDATA%/.lexplosion/libraries\`
- Java: the launcher's \`java-runtime-gamma\`, or Gradle's JDK if not installed
- NWClient JARs: \`workspace/build/dev-artifacts\` (staged by \`devPrepare\`)

**No \`deploy.toml\` is required or read by \`devRun\`, \`devDebug\` or
\`devCheck\`.** These tasks use the committed \`dev-launch-template.txt\` and
the existing Minecraft 1.20 files already installed by the NWLauncher.
The launch template was derived from the existing client launch profile,
without an authlib-injector agent, account tokens, or remote authentication
flags. It uses an **offline development identity only**, suitable for local
UI tests, not authenticated multiplayer or NightWorld services.

The workspace loads the five staged NWClient JARs **directly**, so these
default dev tasks do not overwrite the launcher's installed JARs. The launch
profile still points to the existing \`nwclient dev\` Minecraft instance for
assets, natives and \`client.jar\`. If that instance is not installed, run the
NWLauncher once to create it, or add a separate template in a future task.

\`devCheck\` validates expected files and the classpath without launching.
\`devDebug\` adds JDWP on \`127.0.0.1:5005\`; attach a Remote JVM Debugger in
your IDE. JVM HotSwap and XML Live Reload are separate future tasks.

For an **authenticated** profile, we will need a supported handoff from the
NWLauncher to obtain an authorized *current session*. We do not extract,
invent, or embed credentials in the repository. The historical
\`deploy.toml\`/\`example.deploy.toml\` remain only for legacy/manual workflows;
the default offline dev tasks ignore them.

### Current validation status

The Windows test confirmed \`devClasses\` and \`devPrepare\` built
successfully. The new config-free offline game launch still needs an
end-to-end local Windows test.

## Current scope

- `devClasses`: incrementally compile both Cosmetic and MinecraftApi.Runtime (plus dependencies), without intentionally invoking packaging/remapping. All Java compile tasks use UTF-8 in this workspace.
- `devBuild`: run the current module build tasks. These still include the
  child projects' Windows-only `postBuild` remapping, which is not optimized yet.
- `devPrepare`, `devCheck`, `devRun` and `devDebug` now exist as experimental tasks. The
  existing `build.py` and `deploy.py` remain available but are not invoked
  by these tasks. XML Live Reload is not implemented yet.
- User testing confirmed `devClasses --rerun-tasks` and `devPrepare` succeeded. A real offline Minecraft launch is not yet verified.

Do not store Minecraft access tokens or expanded launch commands in committed
configuration, CI logs, or shared scripts.
