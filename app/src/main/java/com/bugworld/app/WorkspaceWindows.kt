package com.bugworld.app

/** Remembers user-opened windows across native Stage suspension/destruction. */
class WorkspaceWindows(initial: Set<String>) {
    enum class Phase { SHARED, OPENING, STAGE, RETURNING }
    var phase=Phase.SHARED; private set
    var openIds=initial.toSet(); private set
    private var returnIds=emptySet<String>()
    private var returnFrom=Phase.STAGE

    fun opened(id: String) {
        openIds=openIds+id
        // Native window attachment can complete after the Stage snapshot was taken.
        if(phase!=Phase.SHARED) returnIds=returnIds+id
    }
    fun closed(id: String) { openIds=openIds-id; returnIds=returnIds-id }
    fun detached(id: String, closedByUser: Boolean = true) {
        // The system may dispose a minimized window's composition in a Stage.
        // Stage launch can dispose the old Activity before scene-ready arrives.
        // Explicit close requests still use closed(), including during OPENING.
        if(phase==Phase.SHARED && closedByUser) closed(id)
    }
    fun beginStage(): Boolean {
        if(phase!=Phase.SHARED) return false
        returnIds=openIds.toSet(); phase=Phase.OPENING; return true
    }
    fun stageReady(): Set<String> {
        if(phase!=Phase.OPENING) return emptySet()
        phase=Phase.STAGE; return returnIds.toSet()
    }
    fun stageRejected(): Boolean {
        if(phase!=Phase.OPENING) return false
        phase=Phase.SHARED; returnIds=emptySet(); return true
    }
    fun beginReturn(): Boolean {
        if(phase!=Phase.OPENING && phase!=Phase.STAGE) return false
        returnFrom=phase
        phase=Phase.RETURNING; return true
    }
    fun returnFailed() { if(phase==Phase.RETURNING) phase=returnFrom }
    fun finishReturn(primaryWindow: String): Set<String> {
        if(phase!=Phase.RETURNING) return emptySet()
        val result=setOf(primaryWindow) + returnIds
        openIds=result; returnIds=emptySet(); phase=Phase.SHARED
        return result
    }
}
