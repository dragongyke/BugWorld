package com.bugworld.app.interaction

import android.os.SystemClock
import com.pico.spatial.tracking.hand.HandJoint.Index
import com.pico.spatial.tracking.hand.HandPose
import com.pico.spatial.tracking.hand.HandTrackingProvider
import com.pico.spatial.tracking.hmd.HMDTrackingProvider
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.collect

class HandTrackingSession(private val scope: CoroutineScope) : AutoCloseable {
    private val provider=HandTrackingProvider()
    private val headset=HMDTrackingProvider()
    private var job: Job?=null
    private var updated=0L
    private var latest=emptyList<TrackedHand>()
    private val lifecycle=TrackingLifecycle(
        startHead={headset.start()},stopHead={headset.stop()},
        startHands={startHands()},stopHands={stopHands()})
    val headPose get()=if(lifecycle.headActive) headset.latestData?.hmdPose else null
    val hands get()=if(job!=null && SystemClock.elapsedRealtime()-updated<180L) latest else emptyList()
    // Keep the existing joint-distance thresholds consistent with invitation gestures.
    // If two hands are pinching at once, let the first unambiguous offered palm win.
    val pinchingSide get()=hands.singleOrNull { it.pinchGap<.045f }?.side

    fun active(value: Boolean,handPermissionGranted: Boolean) = lifecycle.update(value,handPermissionGranted)

    private fun startHands() {
        job=scope.launch(start=CoroutineStart.UNDISPATCHED) {
            provider.dataFlow.collect { data ->
                latest=listOfNotNull(data.left?.let { tracked(it,HandSide.LEFT) },
                    data.right?.let { tracked(it,HandSide.RIGHT) })
                updated=SystemClock.elapsedRealtime()
            }
        }
        provider.start()
    }

    private fun stopHands() {
        job?.cancel(); job=null; latest=emptyList(); updated=0L
        provider.stop()
    }
    override fun close() { active(false,false) }
}

internal fun tracked(pose: HandPose,side: HandSide): TrackedHand? {
    fun point(index: Index)=pose.handJoints.firstOrNull { it.index==index }?.position
        ?.let { HandPoint(it.x,it.y,it.z) }?.takeIf { it.finite }
    val wrist=point(Index.WRIST) ?: return null
    val tip=point(Index.INDEX_TIP) ?: return null
    val thumb=point(Index.THUMB_TIP) ?: return null
    val gap=tip.distance(thumb)
    fun extended(tipPoint: HandPoint?,base: Index): Boolean {
        val joint=point(base) ?: return false
        return tipPoint!=null && tipPoint.distance(wrist)>joint.distance(wrist)*1.32f
    }
    val open=gap>.038f && extended(tip,Index.INDEX_PROXIMAL) &&
        extended(point(Index.MIDDLE_TIP),Index.MIDDLE_PROXIMAL) &&
        extended(point(Index.RING_TIP),Index.RING_PROXIMAL)
    val surface=if(open) PalmSurface.from(side,point(Index.PALM) ?: return null,wrist,
        point(Index.INDEX_PROXIMAL) ?: return null,point(Index.LITTLE_PROXIMAL) ?: return null) else null
    return TrackedHand(side,tip,gap,surface)
}
