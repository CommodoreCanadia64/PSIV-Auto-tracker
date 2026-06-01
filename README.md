
PS4 Profound Distortion Autotracker

A streamlined tracking suite for the Phantasy Star IV "Profound Distortion" Randomizer. This tool connects your game to a visual dashboard, letting you focus on the run while the software handles the bookkeeping.

Brief Description
This project consists of three parts: a System Tray Application (the .exe) that monitors game memory, lua script that calls out memory addresses, and a Web Dashboard (the .html) that displays your progress. It automatically tracks items, dungeon completions, featuring an OLED-friendly high-contrast HUD.


Installation
Emulator Requirement: This tracker requires BizHawk 2.11  and the gens+ core to function correctly.

Lua Setup: Run the provided Lua script within BizHawk to begin exporting game data.

run the python (bridge) script (linux)
download and launch the sniffer.exe (windows) 

https://commodorecanadia64.github.io/PSIV-Auto-tracker/

Verify Connection: A Green LED at the bottom of the page confirms the dashboard is successfully talking to the system tray app.


How to Use
Automatic Updates: Items, rings, and dungeon flags light up automatically as they are updated in game memory.

Objectives Panel:

Left-Click: Click inside a box to type custom notes or goals.

Right-Click: Toggle a task as "Done". The box will dim and the text will be struck through.

Locations Panel: Locations are grouped by color to match their respective planets (Orange for Motavia, Blue for Dezolis, Magenta for Rykros, and White for Space).

Retrance Mode: You can use the text fields in the Locations panel to make manual notes to track where specific warps or entrances lead.

Resetting: Click the RESET button on the web dashboard to clear all current progress from both the visual display and the system tray memory.

Maps: you can use the map buttons to cycle through each map in a larger format or keep them all grouped.
Pins: display a number of how many chests are in each respective locations, and hover over each pin for a quick tooltip

Created by:
CommodoreCanadia64
