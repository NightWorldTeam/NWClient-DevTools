# NWClient development workspace

This is the **multi-repository Gradle development workspace** on the
`new-architecture` branch. The five Java repositories remain
independent Git repositories; this repo pins them as **real Git submodules**.

## Get started

```powershell
git clone --branch new-architecture --recurse-submodules https://github.com/NightWorldTeam/NWClient-DevTools.git NWClient-Workspace-Test
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
| MinecraftApi | new-architecture | ffe626789382154f187fdc785e14f6f3340828e4 |
| MinecraftApi.Runtime | new-architecture-compat | 1b9acde093164cc8b8ec12c1faf76f2557492dd3 |
| LaunchLinker | new-architecture | 3fbb477c08a37140986b3212646784e5db929341 |
| ReflectionTools | main | 9c2fa0ab48c3aacea24b352289d1269b2aaa8958 |

Submodules pin commits, **not moving branch tips**. Updates must be explicit:

```powershell
git submodule update --init --recursive
git submodule update --remote Cosmetic MinecraftApi MinecraftApi.Runtime LaunchLinker ReflectionTools
git add Cosmetic MinecraftApi MinecraftApi.Runtime LaunchLinker ReflectionTools
git commit -m "chore: update NWClient submodule pins"
```

## Installation discovery

The default offline dev launcher resolves the NWLauncher game-data directory
with this **exact precedence**:

1. **`deploy.toml`**, if it exists in the workspace: read it first. Use its
   configured path, or `%APPDATA%/.lexplosion` when no path is specified.
   It is authoritative regardless of whether
   `NWCLIENT_HOME` or the standard APPDATA installation exists.
2. **`NWCLIENT_HOME`**, if set and the installation is complete.
3. **`%APPDATA%/.lexplosion`**, the normal NWLauncher game-data directory,
   if the installation is complete.

If `deploy.toml` exists, it is always read. Explicit installation paths
override all automatic detection. **If the file does not specify any game
location**, its unspecified path defaults to `%APPDATA%/.lexplosion` —
there is no need to edit the file just to set the standard path.

An explicitly configured but invalid directory produces an error instead
of silently launching a different installation. Invalid TOML also produces
an error. If no `deploy.toml` exists, discovery falls back to
`NWCLIENT_HOME`, then `%APPDATA%/.lexplosion`.

The minimal private override is:

```toml
[launch]
root = "D:/Games/NightWorld"
```

The config also supports `[launch].libraries` or top-level `target`
(pointing to `libraries/org/nightworld`), provided that all specified
paths refer to the same installation. The offline dev tasks read only
installation paths from `deploy.toml`; they ignore any stored launcher
command, Java setting, or authentication tokens.

## IntelliJ IDEA Community Edition 2025.2 — Debug/F5

This workspace is configured for **IntelliJ IDEA Community 2025.2.x on Windows**.
Open the **workspace root directory** (the folder with `settings.gradle`)
using **File → Open**, import it as a Gradle project and use JDK 17.

Two shared configurations are committed in `.run/`:

- `NWClient - Start Debug JVM` (Gradle): runs `devDebugStart`, which
  incrementally compiles and remaps only changed Vanilla JARs, then starts
  Minecraft with `-agentlib:jdwp=...suspend=y,address=127.0.0.1:5005`.
  It returns after the JVM has opened the debugger endpoint, leaving Minecraft
  running. Output: `build/dev-logs/minecraft-debug.log`.
- `NWClient - Minecraft Debug` (Remote JVM Debug): its **Before Launch →
  Run Another Configuration** action runs `NWClient - Start Debug JVM`
  first and then attaches IntelliJ's Java debugger to localhost:5005.
  This enables Java breakpoints before Minecraft begins executing.

Select **NWClient - Minecraft Debug** from the top Run/Debug selector.
Use **Shift+F9** (IntelliJ's default Debug shortcut). For Visual-Studio-like
**F5**, configure IntelliJ **Settings → Keymap → Run → Debug**, add F5,
and resolve any key conflict. Keymaps are per-user and cannot reliably be
forced by a project file. This is a one-time IDE preference.

If the `Before Launch` entry did not import into IntelliJ, edit
`NWClient - Minecraft Debug` → **Modify options → Add before launch task →
Run Another Configuration**, select `NWClient - Start Debug JVM`,
and **Store as project file**. The shared Remote configuration should show
`127.0.0.1:5005` as the target.

If `NWClient - Start Debug JVM` was launched manually and is already
waiting for the debugger on port 5005, the F5 prelaunch task **reuses that
same JVM** rather than trying to start another. The existing process is
matched against its saved PID and expected Java executable. An unrelated
process on port 5005 remains an error.

Closing the IDE debugger might leave the game open. Close Minecraft
before starting a **fresh** debug launch, because JDWP port 5005 can be
owned by only one Minecraft instance. The launcher uses the same installation-path precedence
and offline identity as `devRun`, and does not change installed JARs.

`devRun` remains available for normal launches. IntelliJ's **Debug**
button on a Gradle task by itself debugs the Gradle process, not Minecraft;
use the provided **Remote JVM Debug** configuration.

The IntelliJ configuration files have static XML tests, but
an actual full IntelliJ Debug → Minecraft session, including breakpoints, was confirmed on Windows.

## Plug-and-play Windows development

With no override file, the default tasks are **configuration-free**:

```powershell
git pull
git submodule update --init --recursive
.\Cosmetic\gradlew.bat -p . devCheck
.\Cosmetic\gradlew.bat -p . devRun
# Or run with JDWP remote debugger on 127.0.0.1:5005:
.\Cosmetic\gradlew.bat -p . devDebug
```

- Launcher root: `%APPDATA%/.lexplosion`
- Libraries: `%APPDATA%/.lexplosion/libraries`
- Java: the launcher's `java-runtime-gamma`, or Gradle's JDK if not installed
- NWClient JARs: `workspace/build/dev-artifacts` (staged by `devPrepare`)

**`deploy.toml` is optional.** If it exists, its installation paths override
all automatic discovery for `devRun`, `devDebug`, and `devCheck`.
These tasks use the committed `dev-launch-template.txt` and
the existing Minecraft 1.20 files already installed by the NWLauncher.
The launch template was derived from the existing client launch profile,
without an authlib-injector agent, account tokens, or remote authentication
flags. It uses an **offline development identity only**, suitable for local
UI tests, not authenticated multiplayer or NightWorld services.

The workspace loads the five staged NWClient JARs **directly**, so these
default dev tasks do not overwrite the launcher's installed JARs. The launch
profile still points to the existing `nwclient dev` Minecraft instance for
assets, natives and `client.jar`. If that instance is not installed, run the
NWLauncher once to create it, or add a separate template in a future task.

`devCheck` validates expected files and the classpath without launching.
`devDebug` adds JDWP on `127.0.0.1:5005`; attach a Remote JVM Debugger in
your IDE. JVM HotSwap and XML Live Reload are separate future tasks.

For an **authenticated** profile, we will need a supported handoff from the
NWLauncher to obtain an authorized *current session*. We do not extract,
invent, or embed credentials in the repository. The historical
`deploy.toml`/`example.deploy.toml` remain only for legacy/manual workflows;
the default offline dev tasks use only their installation path fields.

### Current validation status

Windows testing confirmed `devClasses`, `devPrepare`, `devCheck`, IntelliJ\'s Minecraft debugger and working breakpoints. XML Hot Reload and Java HotSwap of a method body in `TabControl` were also verified in Minecraft.

## Java HotSwap — IntelliJ IDEA Community 2025.2

Minecraft already starts with Java 17 JDWP on `127.0.0.1:5005` when
**NWClient - Minecraft Debug** is selected. The debugger can use the JVM's
built-in HotSwap for *method-body changes*; no second Java agent is needed.

**One-time local IntelliJ setup (user preferences, not shared project files):**

1. Open **Settings → Build, Execution, Deployment → Debugger → HotSwap**.
   Set **Reload classes after compilation** to **Always**, and enable
   **Build project before reloading classes**.
2. Under **Settings → Build, Execution, Deployment → Build Tools → Gradle**,
   use **Gradle** in the **Build and run using** field for this workspace.
3. Launch **NWClient - Minecraft Debug** with **Shift+F9**, and open
   the Cosmetics GUI. The Java debugger must be attached.

**Controlled test without Minecraft-mapped method references:**

1. Open
   `MinecraftApi/src/main/java/org/nightworld/minecraftapi/gui/components/TabControl.java`.
2. In the **private computeTabWidth(TabItem tab)** method, change only
   `return Math.max(MIN_TAB_WIDTH, textW + TAB_TEXT_PADDING);` to
   `return Math.max(MIN_TAB_WIDTH, textW + TAB_TEXT_PADDING + 30);`.
   Do not rename members or add fields.
3. Use **Ctrl+F9 (Build Project)** or right-click the file and choose
   **Compile and Reload Modified Files**. If prompted, apply HotSwap.
4. The tab headers on the already-open Cosmetics screen should become
   wider immediately. Confirm in the IntelliJ Debugger event output that
   the modified class was actually reloaded.
5. Revert the source edit and repeat the compile/reload to restore the
   original width without restarting Minecraft.

The JVM does not support adding or deleting fields/methods or changing their
signatures using standard HotSwap; restart F5 after such changes.

**Important: this is an initial test, not yet a verified general-purpose
HotSwap implementation.** Our running Minecraft loads **Vanilla-remapped**
JAR files, whereas IntelliJ may offer *unremapped* `build/classes/java/main`
bytecode. A Java body that calls Minecraft classes or members whose names
change during remapping may be incompatible when redefined directly by the
IDE. The test above deliberately modifies only UI-library arithmetic.
Do not assume that all Cosmetics or MinecraftApi.Runtime classes are safe
to HotSwap until the compatibility test succeeds. If a reload fails or
the game reports `NoSuchMethodError`/`NoClassDefFoundError`, restart the
debug session, which rebuilds the remapped JARs using `devPrepare`.
A remap-aware HotSwap pipeline would be a separate follow-up.

Source: JetBrains IDEA's built-in **Reload modified classes** documentation.
The settings in this section are local to each IntelliJ installation; Git
cannot change those user preferences through the shared `.run` files.

## XML / XAML Hot Reload (experimental)

The workspace pins the `MinecraftApi` branch
`new-architecture`. The launch tasks `devRun` and
`devDebugStart` pass the **workspace root** using the JVM property
`nwclient.xaml.dir`. MinecraftApi.XamlView then reads edited XAML source files
from `Cosmetic/src/main/resources/assets/nightworld/cosmetic/ui/` without
restaging JARs.

1. `git pull`, `git submodule update --init --recursive`, and reload Gradle
   in IntelliJ.
2. Start **NWClient - Minecraft Debug** using Shift+F9 and open an existing
   XAML-backed Cosmetics screen.
3. Edit and save `Cosmetic/src/main/resources/assets/nightworld/cosmetic/ui/cosmetic_settings.xml`.
4. While that screen is open, it checks for saved changes approximately every
   350 ms and replaces its UI element tree automatically.

If XML parsing fails, the old UI remains visible; the error is written to the
Minecraft log. Saving a corrected file triggers another attempt. Reloading
recreates widget instances and clears keyboard focus, so temporary UI state
(including selected tabs and text input) is reset.

The feature watches files only when the JVM option is set. Production builds
and the normal installed launcher do not gain file polling. The JAR packaged
resource remains the fallback if an XML source file is unavailable.

**Verified in a Windows Minecraft session.** This is an
experimental source-watching implementation, not Java class HotSwap or a
general external filesystem watcher.

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
