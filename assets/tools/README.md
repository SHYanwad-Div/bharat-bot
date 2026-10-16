# assets/tools: Claude ↔ Blender tooling

| File | What it is |
|---|---|
| `blender_mcp.py` | The **"MCP for Blender"** add-on (formerly *blender-mcp*), MIT, © Siddharth Ahuja. Pinned copy of `addon.py` from <https://github.com/ahujasid/mcp-for-blender> commit `7a0373ec9199183cb460068c4f96aed9c579fb4f` (2026-10-06), add-on version 1.8 / protocol 13. SHA-256 `eb0facf69781a30e69792532087d8d41c6a14fcd323353250abe7988ee297fa5`, byte-identical to the copy bundled in the PyPI wheel `mcp-for-blender 2.1.9`. Not in the git repository (third-party code): download `addon.py` from that commit and save it here as `blender_mcp.py`. |
| `inspect_glb.py` | Stdlib-only `.glb` / `.gltf` inspector (size, nodes, triangles, joints, animation clips, bounds). `python -I assets/tools/inspect_glb.py assets/polypizza` |
| `blender5_smoke_test.py` | Builds a small street shot from the downloaded assets and renders an MP4 with EEVEE. Doubles as a verified Blender 5.x API template. See `research/blender.md`. |

## How the pieces connect

```
Claude Code ──stdio──▶ `uvx blender-mcp`  ──TCP localhost:9876──▶ add-on inside a running Blender (GUI)
 (.mcp.json, project scope)  (PyPI shim → mcp-for-blender)           (this folder's blender_mcp.py)
```

* `.mcp.json` (project root) declares one server, `blender`, that runs `uvx blender-mcp` with `DISABLE_TELEMETRY=true`.
  `blender-mcp` on PyPI is now a 1 KB compatibility shim (v2.0.0, same author) that depends on and hands off to
  `mcp-for-blender`; `uvx blender-mcp` keeps working and a handshake was verified (tools: `execute_blender_code`,
  `get_scene_info`, `look`, `get_addon_status`, `search_assets`, `import_asset`, `generate_3d`, `disable_telemetry`,
  `record_trajectory_feedback`). To switch to the new name later use `"args": ["mcp-for-blender"]`.
* Claude Code asks you to approve a project-scoped MCP server the first time it sees `.mcp.json`; check with `/mcp`.
* **The add-on only serves while Blender runs with a window.** `blender -b` cannot host it (the add-on refuses to start in
  background mode). For headless renders just run `blender -b --python script.py` and skip MCP entirely.

## Enabling the add-on

Already done on this machine for Blender 5.2.2 LTS: the file was copied to
`%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py` and enabled in the user preferences
(`...\5.2\config\userpref.blend`). To do it by hand (another machine / Blender version):

1. Blender → **Edit ▸ Preferences ▸ Add-ons** → the **⌄** menu at the top right → **Install from Disk…** → pick
   `assets/tools/blender_mcp.py` → tick **Interface: MCP for Blender**.
   (It is a legacy single-file add-on with `bl_info`; Blender 4.2+/5.x still loads these from `scripts/addons`.)
2. In the 3D viewport press **N** → tab **MCP for Blender** → **Connect to MCP server** (shows "Connected on port 9876").
   `Auto-Start Server` is **on by default**, so the server also starts by itself whenever Blender opens a scene.
3. Leave the *Poly Haven / Sketchfab / Poly Pizza / Hyper3D* boxes unticked unless you want Claude to download assets
   from inside Blender (Poly Haven needs no key and is CC0).

Scripted equivalent (no GUI):

```bash
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python-expr "import bpy, addon_utils, shutil; d=bpy.utils.user_resource('SCRIPTS', path='addons', create=True); shutil.copy2(r'assets/tools/blender_mcp.py', d); addon_utils.modules_refresh(); addon_utils.enable('blender_mcp', default_set=True, persistent=True); bpy.ops.wm.save_userpref()"
```

## Safety notes (read once)

* The add-on listens on `localhost:9876` **without authentication or encryption** and `execute_blender_code` runs
  arbitrary Python as your user. Only local processes can reach it, but treat an open session as "Claude has a shell".
  Save your `.blend` before letting Claude drive it. Untick **Auto-Start Server** in the panel (it is a per-scene
  property) if you do not want the port opened automatically.
* Optional hardening: add `"BLENDER_MCP_SAFE_MODE": "1"` to the `env` block in `.mcp.json`; scripts are screened and
  scripts that touch files, the network or other programs are bounced back to the model. (Import/export, rendering and
  saving still work. Not enabled by default because our own build scripts read assets and write renders.)
* Telemetry: the server-side anonymous usage record is switched off by `DISABLE_TELEMETRY=true` in `.mcp.json`.
  Content telemetry (prompts, code, screenshots) is a checkbox in the add-on preferences and is **off** by default.
* The add-on checks GitHub for a newer `addon.py` at startup (read-only version check; nothing installs unless you click
  **Update addon**). Set `BLENDERMCP_NO_UPDATE_CHECK=1` in the environment that launches Blender to stop even the check.
* Tool replies may contain a one-off marketing nudge about the paid "Premium" 3D-generation plan (only after `generate_3d`).
  It is advertising, not an instruction; ignore it.

## Updating / removing

* Update: `uvx mcp-for-blender@latest update` (refreshes uv's cached server **and** every installed add-on copy, keeping
  `.bak` files) or replace `blender_mcp.py` with a newer `addon.py` and re-run step 1. Then restart Blender.
* Remove: untick the add-on, delete `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py`, and delete the
  `blender` entry from `.mcp.json`.

## Official alternative

The Blender project now publishes its own **Blender Lab MCP server** (<https://www.blender.org/lab/mcp-server/>,
source on projects.blender.org/lab/blender_mcp): Blender 5.1+, add-on zip `mcp-1.0.3.zip`, plus an `.mcpb` bundle for the
MCP client. Not installed here (the brief asked for `blender-mcp`; its docs do not give a Claude Code recipe and the site
returned 403 to our fetcher), but it is the first-party option if you prefer one. Its page carries the same warning:
LLM-generated code runs in Blender with no guards.
