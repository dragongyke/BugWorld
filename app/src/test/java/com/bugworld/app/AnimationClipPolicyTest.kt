package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.garden.InsectAction
import com.bugworld.app.garden.InsectAnimationFrame
import com.bugworld.app.spatial.AnimationClipPolicy
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class AnimationClipPolicyTest {
    @Test fun everySpeciesSelectsOnlyClipsPresentInItsPackagedGlb() {
        val expected = mapOf(
            Species.BUTTERFLY to setOf("butterfly_antenna_groom", "butterfly_fly", "butterfly_idle_perch", "butterfly_perch_touch", "butterfly_startle"),
            Species.BEETLE to setOf("flight", "idle", "takeoff", "touch", "walk"),
            Species.LADYBUG to setOf("flight", "idle", "takeoff", "touch", "walk"),
            Species.CATERPILLAR to setOf("caterpillar_crawl", "caterpillar_explore", "caterpillar_idle_breathe", "caterpillar_recoil", "caterpillar_touch_curiosity"),
            Species.DRAGONFLY to setOf("idle","walk","touch","perch","takeoff","flight"),
            Species.HONEYBEE to setOf("idle","walk","touch","perch","takeoff","flight"),
            Species.ANT to setOf("idle","walk","touch","explore","groom"),
            Species.GRASSHOPPER to setOf("idle","walk","touch","perch","takeoff","flight","hop"),
        )
        assertEquals(Species.entries.toSet(),expected.keys)
        for ((species, names) in expected) {
            assertEquals(names, AnimationClipPolicy.clipNames(species))
            val selected = InsectAction.entries.map { AnimationClipPolicy.select(InsectAnimationFrame(species, it)).name }.toSet()
            assertEquals("All reviewed actions must be reachable for $species", names, selected)
            val candidates = listOf(File("src/main/assets/v3/models"), File("app/src/main/assets/v3/models"))
            val glb = candidates.map { File(it, "${species.asset}.glb") }.first { it.isFile }
            val bytes = glb.readBytes()
            val jsonLength = ByteBuffer.wrap(bytes, 12, 4).order(ByteOrder.LITTLE_ENDIAN).int
            val json = String(bytes, 20, jsonLength, Charsets.UTF_8)
            for (name in names) assertTrue("Missing authored clip $name", Regex("\\\"name\\\"\\s*:\\s*\\\"${Regex.escape(name)}\\\"").containsMatchIn(json))
        }
    }

    @Test fun shellLandingReversesReviewedTakeoffWithoutCrossfadingThroughTheShell() {
        for (species in listOf(Species.BEETLE, Species.LADYBUG)) {
            val takeoff = AnimationClipPolicy.select(InsectAnimationFrame(species, InsectAction.TAKEOFF))
            val land = AnimationClipPolicy.select(InsectAnimationFrame(species, InsectAction.LAND))
            assertEquals("takeoff", takeoff.name)
            assertEquals(takeoff.name, land.name)
            assertTrue(land.reverse)
            assertTrue(land.scrub)
            assertFalse(land.loop)
            assertEquals(0f, land.transitionSeconds, 0f)
            assertEquals(1f, land.phase(0f), 0f)
            assertEquals(.5f, land.phase(.5f), 0f)
            assertEquals(0f, land.phase(1f), 0f)
            assertEquals(.4f, land.phase(0f, .4f), 0f)
            assertEquals(.2f, land.phase(.5f, .4f), .0001f)
        }
    }

    @Test fun movementUsesAuthoredCrawlOrWalkAndNeverFlyingCaterpillar() {
        assertEquals("walk", AnimationClipPolicy.select(InsectAnimationFrame(Species.BEETLE, InsectAction.TURN)).name)
        assertEquals("caterpillar_crawl", AnimationClipPolicy.select(InsectAnimationFrame(Species.CATERPILLAR, InsectAction.CRAWL)).name)
        for (action in listOf(InsectAction.TAKEOFF, InsectAction.FLIGHT, InsectAction.LAND)) {
            assertEquals("caterpillar_idle_breathe", AnimationClipPolicy.select(InsectAnimationFrame(Species.CATERPILLAR, action)).name)
        }
    }

    @Test fun handPerchingMakesGroomAndCuriosityClipsReachableInTheRealController() {
        assertEquals("butterfly_antenna_groom", AnimationClipPolicy.select(InsectAnimationFrame(Species.BUTTERFLY, InsectAction.PERCH)).name)
        assertEquals("caterpillar_touch_curiosity", AnimationClipPolicy.select(InsectAnimationFrame(Species.CATERPILLAR, InsectAction.PERCH)).name)
    }

    @Test fun openPreviewUsesFrozenAuthoredRestPoseAndFiniteClipSampling() {
        for (species in Species.entries) {
            val plan = AnimationClipPolicy.select(InsectAnimationFrame(species, InsectAction.FLIGHT, open = true))
            assertTrue(plan.freeze)
            assertFalse(plan.loop)
            assertEquals(0f, plan.phase(.8f), 0f)
            assertEquals(0f, plan.phase(Float.NaN), 0f)
        }
        val takeoff = AnimationClipPolicy.select(InsectAnimationFrame(Species.BEETLE, InsectAction.TAKEOFF))
        assertEquals(.35f, takeoff.phase(0f, .35f), 0f)
        assertEquals(1f, takeoff.phase(2f), 0f)
        assertEquals(0f, takeoff.phase(Float.NaN), 0f)
    }
}
