package com.bugworld.app

import com.bugworld.app.garden.StageFrameStats
import org.junit.Assert.*
import org.junit.Test

class StageFrameStatsTest {
    @Test fun reportsUnclampedStallAndSeparateLogicCost() {
        val stats=StageFrameStats(4)
        assertNull(stats.record(10_000_000L,1_000_000L,500_000L))
        assertNull(stats.record(20_000_000L,2_000_000L,1_000_000L))
        assertNull(stats.record(30_000_000L,3_000_000L,1_500_000L))
        val sample=stats.record(200_000_000L,4_000_000L,2_000_000L)!!
        assertEquals(4,sample.frames)
        assertEquals(20.0,sample.callbackP50Ms,0.0)
        assertEquals(200.0,sample.callbackP95Ms,0.0)
        assertEquals(200.0,sample.callbackMaxMs,0.0)
        assertEquals(2.5,sample.logicWallMeanMs,0.0)
        assertEquals(1.25,sample.logicCpuMeanMs,0.0)
        assertEquals(3,sample.over90HzBudget)
        assertEquals(3,sample.over72HzBudget)
    }

    @Test fun resetDiscardsPartialWindowAndCompletedWindowDoesNotLeak() {
        val stats=StageFrameStats(2)
        stats.record(1_000_000_000L,5_000_000L,4_000_000L)
        stats.reset()
        assertNull(stats.record(10_000_000L,1_000_000L,500_000L))
        val sample=stats.record(10_000_000L,1_000_000L,500_000L)!!
        assertEquals(10.0,sample.callbackMaxMs,0.0)
        assertEquals(0,sample.over72HzBudget)
        assertNull(stats.record(30_000_000L,2_000_000L,1_000_000L))
        assertEquals(30.0,stats.record(30_000_000L,2_000_000L,1_000_000L)!!.callbackMaxMs,0.0)
    }
}
