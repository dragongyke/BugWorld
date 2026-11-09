package com.bugworld.app.spatial

import com.bugworld.app.data.Species
import com.bugworld.app.garden.InsectAction
import com.bugworld.app.garden.InsectAnimationFrame

data class AnimationClipPlan(val name: String, val loop: Boolean, val reverse: Boolean = false,
    val scrub: Boolean = false, val freeze: Boolean = false, val transitionSeconds: Float = 0f) {
    fun phase(progress: Float, startingPhase: Float? = null): Float {
        if (freeze) return 0f
        val p = if (progress.isFinite()) progress.coerceIn(0f,1f) else 0f
        val start = startingPhase?.takeIf { it.isFinite() }?.coerceIn(0f,1f) ?: if (reverse) 1f else 0f
        return start + ((if (reverse) 0f else 1f)-start)*p
    }
}

object AnimationClipPolicy {
    fun clipNames(species: Species): Set<String> = when (species) {
        Species.BUTTERFLY -> setOf("butterfly_antenna_groom","butterfly_fly","butterfly_idle_perch","butterfly_perch_touch","butterfly_startle")
        Species.BEETLE, Species.LADYBUG -> setOf("flight","idle","takeoff","touch","walk")
        Species.CATERPILLAR -> setOf("caterpillar_crawl","caterpillar_explore","caterpillar_idle_breathe","caterpillar_recoil","caterpillar_touch_curiosity")
        Species.DRAGONFLY, Species.HONEYBEE -> setOf("idle","walk","takeoff","flight","touch","perch")
        Species.GRASSHOPPER -> setOf("idle","walk","takeoff","flight","touch","perch","hop")
        Species.ANT -> setOf("idle","walk","touch","explore","groom")
    }

    fun select(frame: InsectAnimationFrame): AnimationClipPlan {
        val rest = when (frame.species) {
            Species.BUTTERFLY -> "butterfly_idle_perch"
            Species.CATERPILLAR -> "caterpillar_idle_breathe"
            else -> "idle"
        }
        // Open preview keeps the approved authored rest pose; no rig bones or meshes are flattened.
        if (frame.open) return AnimationClipPlan(rest,loop=false,freeze=true)
        return when (frame.species) {
            Species.DRAGONFLY, Species.HONEYBEE, Species.GRASSHOPPER -> when (frame.action) {
                InsectAction.TAKEOFF -> AnimationClipPlan("takeoff",loop=false,scrub=true)
                InsectAction.LAND -> AnimationClipPlan("takeoff",loop=false,reverse=true,scrub=true)
                InsectAction.FLIGHT -> AnimationClipPlan("flight",loop=true)
                InsectAction.HOP -> if (frame.species==Species.GRASSHOPPER) AnimationClipPlan("hop",loop=false,scrub=true) else AnimationClipPlan("flight",loop=true)
                InsectAction.PERCH -> AnimationClipPlan("perch",loop=true,transitionSeconds=.1f)
                InsectAction.WALK, InsectAction.TURN -> AnimationClipPlan("walk",loop=true)
                InsectAction.TOUCH -> AnimationClipPlan("touch",loop=false,scrub=true)
                else -> AnimationClipPlan(rest,loop=true)
            }
            Species.ANT -> when (frame.action) {
                InsectAction.WALK, InsectAction.TURN -> AnimationClipPlan("walk",loop=true)
                InsectAction.TOUCH -> AnimationClipPlan("touch",loop=false,scrub=true)
                InsectAction.EXPLORE -> AnimationClipPlan("explore",loop=false,scrub=true)
                InsectAction.GROOM -> AnimationClipPlan("groom",loop=false,scrub=true)
                else -> AnimationClipPlan(rest,loop=true)
            }
            Species.BEETLE, Species.LADYBUG -> when (frame.action) {
                InsectAction.TAKEOFF -> AnimationClipPlan("takeoff",loop=false,scrub=true)
                InsectAction.LAND -> AnimationClipPlan("takeoff",loop=false,reverse=true,scrub=true)
                InsectAction.FLIGHT -> AnimationClipPlan("flight",loop=true)
                InsectAction.WALK, InsectAction.TURN, InsectAction.CRAWL, InsectAction.EXPLORE -> AnimationClipPlan("walk",loop=true)
                InsectAction.TOUCH, InsectAction.RECOIL -> AnimationClipPlan("touch",loop=false,scrub=true)
                else -> AnimationClipPlan(rest,loop=true)
            }
            Species.BUTTERFLY -> when (frame.action) {
                InsectAction.FLIGHT -> AnimationClipPlan("butterfly_fly",loop=true,transitionSeconds=.12f)
                InsectAction.TAKEOFF, InsectAction.RECOIL -> AnimationClipPlan("butterfly_startle",loop=false,scrub=true)
                InsectAction.TOUCH -> AnimationClipPlan("butterfly_perch_touch",loop=false,scrub=true)
                InsectAction.EXPLORE, InsectAction.PERCH -> AnimationClipPlan("butterfly_antenna_groom",loop=true,transitionSeconds=.12f)
                else -> AnimationClipPlan(rest,loop=true,transitionSeconds=.12f)
            }
            Species.CATERPILLAR -> when (frame.action) {
                InsectAction.WALK, InsectAction.TURN, InsectAction.CRAWL -> AnimationClipPlan("caterpillar_crawl",loop=true,transitionSeconds=.12f)
                InsectAction.EXPLORE -> AnimationClipPlan("caterpillar_explore",loop=false,scrub=true)
                InsectAction.TOUCH -> AnimationClipPlan("caterpillar_touch_curiosity",loop=false,scrub=true)
                InsectAction.PERCH -> AnimationClipPlan("caterpillar_touch_curiosity",loop=true,transitionSeconds=.12f)
                InsectAction.RECOIL -> AnimationClipPlan("caterpillar_recoil",loop=false,scrub=true)
                else -> AnimationClipPlan(rest,loop=true,transitionSeconds=.12f)
            }
        }
    }
}
