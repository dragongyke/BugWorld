package com.bugworld.app.garden

/** Requires rendered frames after preparation; frames spent loading do not count. */
class SceneReadiness {
    private var frames = 0
    fun frame(visible: Boolean, prepared: Boolean): Boolean {
        frames = if (visible && prepared) frames + 1 else 0
        return frames >= 3
    }
    fun reset() { frames = 0 }
}
