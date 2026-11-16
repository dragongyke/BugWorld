package com.bugworld.app.interaction

/** Hand permission must not disable the HMD pose used to place the garden. */
internal class TrackingLifecycle(
    private val startHead: ()->Unit,
    private val stopHead: ()->Unit,
    private val startHands: ()->Unit,
    private val stopHands: ()->Unit
) {
    var headActive=false
        private set
    var handsActive=false
        private set

    fun update(active: Boolean,handPermissionGranted: Boolean) {
        if(!active) {
            try { stopHandTracking() } finally {
                if(headActive) { headActive=false;stopHead() }
            }
            return
        }
        if(!headActive) { startHead();headActive=true }
        if(!handPermissionGranted) stopHandTracking()
        else if(!handsActive) {
            try { startHands();handsActive=true }
            catch(error: Exception) {
                runCatching { stopHands() }.exceptionOrNull()?.let(error::addSuppressed)
                throw error
            }
        }
    }

    private fun stopHandTracking() {
        if(handsActive) { handsActive=false;stopHands() }
    }
}
