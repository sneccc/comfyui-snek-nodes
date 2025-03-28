import { app } from "/scripts/app.js";

// Helper function to fetch modes for a given filename
async function getModesForFile(filename) {
    try {
        const response = await fetch(`/snek/get_modes/${encodeURIComponent(filename)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const modes = await response.json();
        // Ensure "all" is always first if present
        if (modes.includes("all")) {
            return ["all", ...modes.filter(m => m !== "all").sort()];
        }
        return modes.sort(); // Sort alphabetically if "all" is not present
    } catch (error) {
        console.error(`Error fetching modes for ${filename}:`, error);
        return ["all"]; // Fallback to just "all" on error
    }
}

// Register the extension
app.registerExtension({
    name: "Snek.RandomPrompt.DynamicModes",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Check if this is the target node type
        if (nodeData.name === "🐍 Random Prompt From JSON") {

            // Find the original onConfigure method if it exists
            const onConfigure = nodeType.prototype.onConfigure;

            // Monkey patch onConfigure to run our logic after the node is configured
            nodeType.prototype.onConfigure = async function () {
                // Call the original onConfigure if it exists
                if (onConfigure) {
                    onConfigure.apply(this, arguments);
                }

                // Find the widgets within this specific node instance
                const jsonFileWidget = this.widgets.find(w => w.name === "json_file");
                const modeWidget = this.widgets.find(w => w.name === "mode");

                if (!jsonFileWidget || !modeWidget) {
                    console.error("Could not find json_file or mode widget in RandomPromptFromJson node.");
                    return;
                }

                // Store the original callback to avoid issues if it's modified elsewhere
                const originalCallback = jsonFileWidget.callback;

                // Wrap the existing callback (if any) or create a new one
                jsonFileWidget.callback = async (value) => {
                    // Run the original callback first if it existed
                    if (originalCallback) {
                        originalCallback.call(jsonFileWidget, value);
                    }

                    console.log(`Selected JSON file: ${value}`);
                    const newModes = await getModesForFile(value);
                    console.log("Fetched modes:", newModes);

                    // --- Update Mode Widget ---
                    const currentModeValue = modeWidget.value; // Remember the current selection

                    // Update the options available in the dropdown
                    modeWidget.options.values = newModes;

                    // Check if the previously selected mode is still valid
                    if (newModes.includes(currentModeValue)) {
                        modeWidget.value = currentModeValue; // Keep the selection
                        // Need to manually update the displayed text if using LiteGraph default combo
                        if (modeWidget.inputEl) { // Check if inputEl exists (standard combo)
                             modeWidget.inputEl.value = currentModeValue;
                        }
                         // For ComfyUI's custom combo, setting value might be enough,
                         // but LiteGraph might need manual text update. Might need adjustment
                         // based on exact widget type ComfyUI uses internally.
                    } else {
                        // If previous selection is invalid, default to "all"
                        modeWidget.value = "all";
                         if (modeWidget.inputEl) {
                            modeWidget.inputEl.value = "all";
                         }
                    }

                     // Trigger node redraw or widget update if necessary (might not be needed)
                     // this.setDirtyCanvas(true, true); // May cause excessive redraws

                     console.log("Mode widget updated. New value:", modeWidget.value);
                };

                 // --- Initial population (optional but good practice) ---
                 // Trigger the callback manually on load for the initially selected file
                 // Use a small timeout to ensure the node is fully ready
                 setTimeout(() => {
                    if (jsonFileWidget.value) { // Check if a file is selected initially
                         jsonFileWidget.callback(jsonFileWidget.value);
                    }
                 }, 100); // 100ms delay, adjust if needed

            }; // end onConfigure patch
        }
    },
}); 