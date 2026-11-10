package com.bugworld.app

import com.bugworld.app.ui.PaperSurfaceHealth
import com.bugworld.app.ui.PaperSurfaceHealth.Status.*
import org.junit.Assert.assertEquals
import org.junit.Test

class PaperSurfaceHealthTest {
    @Test fun enabledEntityWithoutDisplayedContentCannotPass() {
        val health = PaperSurfaceHealth()
        assertEquals(WAITING, health.sample(0, true, false))
        assertEquals(WAITING, health.sample(5_999, true, false))
        assertEquals(FAILED, health.sample(6_000, true, false))
    }
    @Test fun headsetSleepDoesNotConsumeRecoveryBudget() {
        val health = PaperSurfaceHealth()
        health.sample(0, true, false)
        assertEquals(WAITING, health.sample(1_000, false, false))
        assertEquals(WAITING, health.sample(120_000, true, false))
        assertEquals(READY, health.sample(120_250, true, true))
    }
    @Test fun lostSurfaceAfterSuccessHasItsOwnRecoveryWindow() {
        val health = PaperSurfaceHealth()
        health.sample(0, true, false)
        assertEquals(READY, health.sample(500, true, true))
        assertEquals(WAITING, health.sample(10_000, true, false))
        assertEquals(WAITING, health.sample(15_999, true, false))
        assertEquals(FAILED, health.sample(16_000, true, false))
    }
}
