package com.bugworld.app

import com.bugworld.app.garden.SceneReadiness
import org.junit.Assert.*
import org.junit.Test

class SceneReadinessTest {
    @Test fun loadingFramesNeverReleaseAnInsect() {
        val gate=SceneReadiness()
        repeat(120) { assertFalse(gate.frame(true,false)) }
        assertFalse(gate.frame(true,true)); assertFalse(gate.frame(true,true))
        assertTrue(gate.frame(true,true))
    }
    @Test fun hiddenOrUnpreparedSceneMustWarmUpAgain() {
        val gate=SceneReadiness()
        repeat(3) { gate.frame(true,true) }
        assertFalse(gate.frame(false,true))
        assertFalse(gate.frame(true,true))
        assertFalse(gate.frame(true,false))
        assertFalse(gate.frame(true,true)); assertFalse(gate.frame(true,true))
        assertTrue(gate.frame(true,true))
        gate.reset(); assertFalse(gate.frame(true,true))
    }
}
