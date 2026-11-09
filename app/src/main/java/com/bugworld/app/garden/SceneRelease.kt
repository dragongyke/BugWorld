package com.bugworld.app.garden

/** A release is committed once, only after the stage and its resources are ready. */
class SceneRelease {
    data class Request(val artworkId: String, val generation: Long)
    var pending: Request? = null; private set
    private var generation = 0L
    private var claimed = false

    fun request(artworkId: String): Request {
        pending?.takeIf { it.artworkId == artworkId }?.let { return it }
        return Request(artworkId, ++generation).also { pending = it; claimed = false }
    }
    fun claim(sceneVisible: Boolean, resourcesReady: Boolean): Request? {
        if (!sceneVisible || !resourcesReady || claimed) return null
        return pending?.also { claimed = true }
    }
    fun isCurrent(request: Request) = pending == request
    fun complete(request: Request): Boolean {
        if (!claimed || pending != request) return false
        pending = null; claimed = false
        return true
    }
    fun retry(request: Request) { if (pending == request) claimed = false }
    fun cancel() { pending = null; claimed = false }
}
