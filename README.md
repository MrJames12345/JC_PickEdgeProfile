To see current profile number:
- chrome://version/
- Value under "Profile path"

### Browser Window Position and Size
`settings.json`'s `windowOpenGeometry` configures the browser windows launched for every profile opened from `Dashboard.py`:
- **Monitor 1 window**: `{"x": 18, "y": 24, "width": 871, "height": 1639}` (`left=18, top=24, right=889, bottom=1663`)
- **Monitor 2 window**: `{"x": 3090, "y": 24, "width": 2155, "height": 1639}` (`left=3090, top=24, right=5245, bottom=1663`)

### Profile Editing Modal
- **Shift + Click** on any profile tile (or press **Shift + Enter** on the matched profile) to open the edit modal.
- Configurable options:
  - **Open Chrome 1 (Small)**: Toggle Monitor 1 browser window. When ticked, displays the list of URL tiles to open on this window, with drag-and-drop reordering (drag `::` handle or tile up/down), a `+` button to add URLs, and `✕` to delete.
  - **Open Chrome 2 (Large)**: Toggle Monitor 2 browser window. When ticked, displays the list of URL tiles to open on this window, with drag-and-drop reordering (drag `::` handle or tile up/down), a `+` button to add URLs, and `✕` to delete.
  - **Open JC_TheGoodWorkspace**: Toggle whether to launch JC_TheGoodWorkStation with the profile's workspace/folder.
- Settings are saved directly to `profiles.json`.

---

## PickJcProject Dashboard

A simple dashboard to quickly pick and open JC projects in JC_TheGoodWorkStation.

### Usage
Run `PickJcProject.vbs` to launch the dashboard without a console window.
Press `Esc` to close the dashboard.

### Features
- Scans `C:\repo` for all folders starting with `JC_`.
- Premium dark theme UI with hover effects.
- Type to search: start typing any characters to filter projects in real-time. Press `Enter` to open the first match, or `Esc` to clear search / exit.
- Automatically positions on the second monitor.
- Opens the `.code-workspace` file if present, otherwise opens the folder.