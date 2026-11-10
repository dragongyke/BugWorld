package com.bugworld.app.interaction

import com.bugworld.app.data.Species
import com.pico.spatial.core.math.EulerAngles
import com.pico.spatial.core.math.Quat
import kotlin.math.*

enum class HandSide { LEFT, RIGHT }

data class PalmSurface(val side: HandSide,val center: HandPoint,val normal: HandPoint,
    val fingers: HandPoint,val breadth: Float) {
    /** Convert every input through the same garden root; vectors must not pick up its translation. */
    fun inSpace(convert: (HandPoint)->HandPoint): PalmSurface {
        val local=convert(center)
        return copy(center=local,normal=convert(center+normal)-local,fingers=convert(center+fingers)-local)
    }
    fun perch(species: Species,eye: HandPoint,step: Float): PerchPose {
        val toward=eye-center
        val projected=toward-normal*toward.dot(normal)
        // Directly above the hand there is no unique projected gaze direction.
        val heading=if(projected.dot(projected)>.025f*.025f) projected.unit()!! else fingers
        val x: HandPoint; val z: HandPoint
        if(species==Species.BUTTERFLY) { z=heading*(-1f); x=normal.cross(z) }
        else { x=heading; z=x.cross(normal) }
        val rad=180f/PI.toFloat()
        val orientation=EulerAngles(asin((-z.y).coerceIn(-1f,1f))*rad,
            atan2(z.x,z.z)*rad,atan2(x.y,normal.y)*rad).toQuat()
        // PALM is a joint center. The GLBs have foot-level normalized origins, so offset
        // to the skin plus a small species-specific sole clearance, in meters.
        val clearance=when(species) { Species.BUTTERFLY->.001f; Species.LADYBUG->.0015f; else->.002f }
        // The system hand silhouette can extend past the joint-derived skin plane.
        // Keep the extra separation along the palm normal as the hand tilts.
        val matteClearance = (breadth * .10f).coerceIn(.005f, .009f)
        val point=center+normal*(breadth*.14f+clearance+matteClearance)+heading*step
        return PerchPose(point,orientation)
    }

    companion object {
        fun from(side: HandSide,palm: HandPoint,wrist: HandPoint,index: HandPoint,little: HandPoint): PalmSurface? {
            val span=index.distance(little)
            if(!palm.finite || span !in .025f.. .12f) return null
            val n=(index-wrist).cross(little-wrist).unit() ?: return null
            val normal=n*(if(side==HandSide.RIGHT) 1f else -1f)
            val fingers=((index+little)*.5f-wrist).unit() ?: return null
            return PalmSurface(side,palm,normal,fingers,span)
        }
    }
}

data class PerchPose(val point: HandPoint,val orientation: Quat)

data class TrackedHand(val side: HandSide,val indexTip: HandPoint,val pinchGap: Float,val open: PalmSurface?)

/** A native target pinch picks the resident. A fresh, open palm chooses only its landing surface. */
class HandInvitation {
    var surface: PalmSurface?=null; private set
    var targetId: String?=null; private set
    var landedFor: Float?=null; private set
    private var stable=0f
    private var elapsed=0f
    private var cooldown=0f
    val canInvite get()=stable>=.45f && targetId==null && cooldown<=0f
    fun update(palms: List<PalmSurface>,preferred: HandSide?,delta: Float) {
        cooldown=(cooldown-delta).coerceAtLeast(0f)
        val previous=surface
        val eligible=palms.filter { it.normal.y>.22f && it.center.finite }
        // Once a visit starts, never transplant a resident to the other hand.
        val next=if(targetId!=null) eligible.find { it.side==previous?.side }
            else eligible.find { it.side==preferred } ?: eligible.find { it.side==previous?.side } ?: eligible.firstOrNull()
        val same=previous!=null && previous.side==next?.side
        val distance=if(same) previous!!.center.distance(next!!.center) else 0f
        if(next==null || targetId!=null && distance>.40f) {
            if(targetId!=null) cancel()
            stable=0f; surface=null; return
        }
        surface=next
        stable=if(!same || distance>maxOf(.012f,delta*.38f)) 0f else stable+delta
        if(targetId!=null) {
            elapsed+=delta
            landedFor=landedFor?.plus(delta)
            if((landedFor ?: 0f)>=3f || landedFor==null && elapsed>12f) cancel()
        }
    }
    fun begin(id: String) { if(canInvite) { targetId=id; elapsed=0f; landedFor=null } }
    fun landed(id: String) { if(targetId==id && landedFor==null) landedFor=0f }
    fun cancel() { targetId=null; stable=0f; elapsed=0f; landedFor=null; cooldown=2f }
    fun reset() { surface=null; targetId=null; stable=0f; elapsed=0f; landedFor=null; cooldown=0f }
}
