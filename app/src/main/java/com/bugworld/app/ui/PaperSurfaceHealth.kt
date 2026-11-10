package com.bugworld.app.ui

/** Measures continuous foreground time without a displayed native paper, not entity attachment. */
internal class PaperSurfaceHealth(private val timeoutMillis: Long = 6_000) {
    enum class Status { WAITING, READY, FAILED }
    private var missingSince: Long? = null

    fun sample(nowMillis: Long, foreground: Boolean, contentShown: Boolean): Status {
        if (!foreground || contentShown) {
            missingSince = null
            return if (foreground && contentShown) Status.READY else Status.WAITING
        }
        val since = missingSince ?: nowMillis.also { missingSince = it }
        return if (nowMillis - since >= timeoutMillis) Status.FAILED else Status.WAITING
    }
}
