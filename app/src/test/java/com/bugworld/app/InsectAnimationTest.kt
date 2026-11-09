package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.garden.*
import org.junit.Assert.*
import org.junit.Test

class InsectAnimationTest {
    @Test fun caterpillarDistinguishesGentleCuriosityFromQuickRecoil() {
        assertEquals(InsectAction.TOUCH,InsectAnimationController(Species.CATERPILLAR).update(.02f,reaction=.7f).action)
        assertEquals(InsectAction.RECOIL,InsectAnimationController(Species.CATERPILLAR).update(.02f,reaction=1f).action)
    }
    private fun settle(controller: InsectAnimationController, seconds: Float = 2f,
        moving: Boolean = false, flying: Boolean = false, onHand: Boolean = false,
        reaction: Float = 0f, turning: Float = 0f, retiring: Boolean = false): InsectAnimationFrame {
        var frame = controller.update(0f)
        repeat((seconds / .02f).toInt()) {
            frame = controller.update(.02f,moving,turning,flying,onHand,reaction,retiring=retiring)
        }
        return frame
    }

    @Test fun everyFlyingSpeciesOpensBeforeFlightAndClosesAfterLanding() {
        for(species in Species.entries.filter { it.canFly }) {
            val controller = InsectAnimationController(species)
            assertEquals(InsectAction.TAKEOFF,controller.update(.02f,flying=true).action)
            val flying = settle(controller,flying=true)
            assertEquals(InsectAction.FLIGHT,flying.action)
            assertEquals(1f,flying.flightBlend,.001f)
            assertEquals(1f,flying.shellOpen,.001f)
            assertEquals(InsectAction.LAND,controller.update(.02f,onHand=true).action)
            val landed = settle(controller,onHand=true)
            assertEquals(InsectAction.PERCH,landed.action)
            assertEquals(0f,landed.flightBlend,.001f)
            assertEquals(0f,landed.shellOpen,.001f)
        }
    }

    @Test fun cancelledTakeoffAndLandingKeepContinuousFlightWeights() {
        val controller = InsectAnimationController(Species.BEETLE)
        val start = settle(controller,.7f,flying=true)
        val cancelled = controller.update(.01f,flying=false)
        assertEquals(InsectAction.LAND,cancelled.action)
        assertTrue(kotlin.math.abs(cancelled.flightBlend-start.flightBlend)<.08f)
        val resumed = controller.update(.01f,flying=true)
        assertEquals(InsectAction.TAKEOFF,resumed.action)
        assertTrue(kotlin.math.abs(resumed.flightBlend-cancelled.flightBlend)<.08f)
        assertEquals(InsectAction.IDLE,settle(controller).action)
    }

    @Test fun touchStopsGroundGaitButDoesNotFoldAnAirborneInsect() {
        val walking = InsectAnimationController(Species.LADYBUG)
        settle(walking,moving=true)
        val before = walking.update(.02f,moving=true)
        val touched = walking.update(.02f,moving=true,reaction=1f)
        assertEquals(InsectAction.TOUCH,touched.action)
        assertEquals(0f,touched.motion,0f)
        assertEquals(before.gaitPhase,touched.gaitPhase,.0001f)
        val flying = InsectAnimationController(Species.BUTTERFLY)
        settle(flying,flying=true)
        val airTouch = flying.update(.02f,flying=true,reaction=1f)
        assertEquals(InsectAction.FLIGHT,airTouch.action)
        assertEquals(1f,airTouch.flightBlend,.001f)
    }

    @Test fun sustainedTouchDoesNotRestartOrAccumulateReaction() {
        val controller = InsectAnimationController(Species.CATERPILLAR)
        assertEquals(InsectAction.RECOIL,controller.update(.02f,reaction=1f).action)
        val released = settle(controller,3f,reaction=1f)
        assertNotEquals(InsectAction.RECOIL,released.action)
        assertEquals(0f,released.reaction,.001f)
        settle(controller,.2f,reaction=0f)
        assertEquals(InsectAction.RECOIL,controller.update(.02f,reaction=1f).action)
    }

    @Test fun caterpillarHasFiveGroundActionsAndNeverTakesFlight() {
        val controller = InsectAnimationController(Species.CATERPILLAR)
        val seen = mutableSetOf<InsectAction>()
        repeat(400) { seen += controller.update(.02f,flying=true).action }
        seen += controller.update(.02f,moving=true).action
        seen += controller.update(.02f,moving=true,turning=.8f).action
        seen += controller.update(.02f,reaction=1f).action
        assertTrue(seen.containsAll(listOf(InsectAction.IDLE,InsectAction.EXPLORE,InsectAction.CRAWL,InsectAction.TURN,InsectAction.RECOIL)))
        assertFalse(seen.any { it in listOf(InsectAction.TAKEOFF,InsectAction.FLIGHT,InsectAction.LAND) })
    }

    @Test fun retirementOverridesHandPerchAndTouchForFlyingSpecies() {
        val controller = InsectAnimationController(Species.BEETLE)
        settle(controller,onHand=true)
        val leaving = controller.update(.02f,onHand=true,reaction=1f,retiring=true)
        assertEquals(InsectAction.TAKEOFF,leaving.action)
        assertEquals(InsectAction.FLIGHT,settle(controller,retiring=true,onHand=true).action)
    }

    @Test fun restingGaitStopsAndInstancesKeepIndependentPhases() {
        val a = InsectAnimationController(Species.BEETLE,.1f)
        val b = InsectAnimationController(Species.BEETLE,.8f)
        val first = a.update(.02f)
        val last = settle(a)
        assertEquals(first.gaitPhase,last.gaitPhase,0f)
        assertNotEquals(first.wingPhase,b.update(.02f).wingPhase)
        val hand = settle(a,moving=true,onHand=true)
        assertEquals(0f,hand.motion,0f)
    }

    @Test fun invalidDeltaDoesNotPoisonClockAndLargeResumeDoesNotSkipTransitions() {
        val controller = InsectAnimationController(Species.BUTTERFLY)
        val zero = controller.update(0f)
        for(dt in listOf(Float.NaN,Float.POSITIVE_INFINITY,-1f)) {
            val frame = controller.update(dt)
            assertEquals(zero.elapsedSeconds,frame.elapsedSeconds,0f)
            assertTrue(frame.wingPhase.isFinite())
        }
        val resumed = controller.update(100f,flying=true)
        assertEquals(InsectAction.TAKEOFF,resumed.action)
        assertTrue(resumed.progress<.3f)
    }

    @Test fun shellsClearMembranesBeforeThrustAndStayOpenUntilFlightStops() {
        for(species in listOf(Species.BEETLE,Species.LADYBUG)) {
            val controller = InsectAnimationController(species)
            repeat(100) {
                val frame = controller.update(.02f,flying=true)
                if(frame.flightBlend>.05f) assertTrue(frame.shellOpen>.99f)
            }
            repeat(100) {
                val frame = controller.update(.02f)
                if(frame.flightBlend>.001f) assertTrue(frame.shellOpen>.99f)
            }
        }
    }

    @Test fun allSpeciesExposeAtLeastFiveActionsWithFiniteBoundedPoseWeights() {
        for(species in Species.entries) {
            val controller = InsectAnimationController(species,.4f)
            val actions = mutableSetOf<InsectAction>()
            repeat(900) { tick ->
                val frame = controller.update(.02f,
                    moving=tick in 250..399,turning=if(tick in 320..399) -1f else 0f,
                    flying=tick in 500..650,onHand=tick in 700..750,
                    reaction=if(tick in 420..480) 1f else 0f)
                actions += frame.action
                for(value in listOf(frame.progress,frame.flightBlend,frame.shellOpen,frame.reaction,frame.exploration)) {
                    assertTrue("$species ${frame.action}: $value",value.isFinite() && value in 0f..1f)
                }
            }
            assertTrue("$species $actions",actions.size>=5)
        }
    }
}
