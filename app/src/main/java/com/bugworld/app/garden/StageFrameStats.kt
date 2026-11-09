package com.bugworld.app.garden

import kotlin.math.ceil

/** App callback cadence and local logic cost. Neither is a measurement of renderer/compositor FPS. */
class StageFrameStats(private val window: Int=300) {
    init { require(window>0) }
    private val intervals=LongArray(window)
    private var count=0
    private var wall=0L
    private var cpu=0L
    data class Sample(val frames: Int,val callbackP50Ms: Double,val callbackP95Ms: Double,
        val callbackMaxMs: Double,val logicWallMeanMs: Double,val logicCpuMeanMs: Double,
        val over90HzBudget: Int,val over72HzBudget: Int)

    fun record(intervalNanos: Long,logicWallNanos: Long,logicCpuNanos: Long): Sample? {
        intervals[count++]=intervalNanos
        wall+=logicWallNanos; cpu+=logicCpuNanos
        if(count<window) return null
        intervals.sort()
        fun percentile(fraction: Double)=intervals[(ceil(window*fraction).toInt()-1).coerceAtLeast(0)]/1_000_000.0
        val result=Sample(window,percentile(.5),percentile(.95),intervals.last()/1_000_000.0,
            wall/window/1_000_000.0,cpu/window/1_000_000.0,
            intervals.count { it>1_000_000_000L/90 },intervals.count { it>1_000_000_000L/72 })
        reset()
        return result
    }
    fun reset() { count=0; wall=0L; cpu=0L }
}
