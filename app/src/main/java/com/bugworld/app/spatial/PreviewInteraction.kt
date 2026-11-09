package com.bugworld.app.spatial

import com.pico.spatial.core.math.EulerAngles
import com.pico.spatial.core.math.Quat
import kotlin.math.abs

/** Input and model quaternions are in the preview parent's spatial axes. */
class PreviewInteraction {
    var orientation=EulerAngles(60f,0f,0f).toQuat(); private set
    private data class Grip(val id: Long,val began: Long,val poke: Boolean,
        var hand: Quat?,var model: Quat,var lastSample: Long,var rotated: Boolean=false)
    private var grip: Grip?=null
    private var lastTouch: Long?=null
    private var pendingReaction=0f

    fun down(id: Long,hand: Quat?,timeMs: Long,poke: Boolean) {
        if(grip!=null) return
        grip=Grip(id,timeMs,poke,hand,orientation,timeMs)
        if(poke) touch(timeMs)
    }
    fun sample(id: Long,hand: Quat?,timeMs: Long) {
        val current=grip ?: return
        if(current.id!=id || current.poke) return
        val start=current.hand
        if(hand==null || start==null || timeMs-current.lastSample !in 0..300) {
            current.hand=hand; current.model=orientation
        } else {
            val delta=hand*start.conjugate()
            // Ignore sub-three-degree jitter on a brief tap; quaternion signs represent the same pose.
            if(abs(delta.w)<.999657f) current.rotated=true
            if(current.rotated) orientation=(delta*current.model).normalize()
        }
        current.lastSample=timeMs
    }
    fun up(id: Long,timeMs: Long) {
        val current=grip ?: return
        if(current.id!=id) return
        grip=null
        if(!current.poke && !current.rotated && timeMs-current.began in 0..650) touch(timeMs)
    }
    fun releaseMissing(pointerIds: List<Long>) {
        if(grip?.id !in pointerIds) grip=null
    }
    private fun touch(timeMs: Long) {
        if(lastTouch?.let { timeMs-it<2100 }==true) return
        lastTouch=timeMs; pendingReaction=.7f
    }
    fun takeReaction(): Float = pendingReaction.also { pendingReaction=0f }
    fun cancel() { grip=null; pendingReaction=0f }
}
