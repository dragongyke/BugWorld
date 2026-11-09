package com.bugworld.app.interaction

import com.bugworld.app.data.Species
import kotlin.math.PI
import kotlin.math.sin

enum class GardenGestureResponse { IGNORE, RESPOND, RESPOND_AND_SELECT }

/** Native target input acknowledges the chosen resident; a hand pose never chooses a target. */
object GardenInteractionPolicy {
    const val REACTION=.7f

    fun gesture(species: Species,poke: Boolean,inBirth: Boolean=false,retiring: Boolean=false,
        visiting: Boolean=false,secondsSinceTouch: Float=Float.POSITIVE_INFINITY): GardenGestureResponse {
        if(inBirth || retiring || visiting || secondsSinceTouch<=2.5f || secondsSinceTouch.isNaN())
            return GardenGestureResponse.IGNORE
        return if(!poke && species.canFly)
            GardenGestureResponse.RESPOND_AND_SELECT else GardenGestureResponse.RESPOND
    }

    fun canInvite(species: Species,handDistance: Float?,stableHand: Boolean,inBirth: Boolean=false,
        retiring: Boolean=false,visiting: Boolean=false,responding: Boolean=false): Boolean {
        if(!stableHand || handDistance==null || !handDistance.isFinite() || handDistance<0f ||
            inBirth || retiring || visiting || responding) return false
        return species.canFly
    }

    /** A brief body turn acknowledges airborne input without interrupting the authored flight clip. */
    fun airborneResponseYaw(species: Species,secondsSinceTouch: Float): Float {
        if(!secondsSinceTouch.isFinite() || secondsSinceTouch<=0f || secondsSinceTouch>=.8f) return 0f
        val amplitude=when(species) { Species.BUTTERFLY,Species.DRAGONFLY->10f; Species.ANT,Species.CATERPILLAR->0f; else->6f }
        return sin(secondsSinceTouch/.8f*PI.toFloat())*amplitude
    }
}

data class GardenInteractionCue(val residentId: String,val title: Int,val instruction: Int,val species: Species?=null)
