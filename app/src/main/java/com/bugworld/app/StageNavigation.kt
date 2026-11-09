package com.bugworld.app

/** Keep shared windows usable unless the system actually grants the stage. */
class StageNavigation(private val open: suspend ()->Boolean,private val hideWindows: ()->Unit) {
    suspend fun enter(): Boolean {
        if(!open()) return false
        hideWindows(); return true
    }
}
