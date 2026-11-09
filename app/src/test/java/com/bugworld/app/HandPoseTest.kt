package com.bugworld.app

import com.bugworld.app.interaction.*
import com.pico.spatial.core.math.Quat
import com.pico.spatial.core.math.Vector3
import com.pico.spatial.tracking.hand.HandJoint
import com.pico.spatial.tracking.hand.HandJoint.Index
import com.pico.spatial.tracking.hand.HandPose
import org.junit.Assert.*
import org.junit.Test

class HandPoseTest {
    private val joints=mapOf(Index.WRIST to Vector3(0f,1f,-.4f),Index.PALM to Vector3(0f,1f,-.45f),
        Index.THUMB_TIP to Vector3(.08f,1f,-.50f),Index.INDEX_PROXIMAL to Vector3(.035f,1f,-.49f),
        Index.INDEX_TIP to Vector3(.035f,1f,-.56f),Index.MIDDLE_PROXIMAL to Vector3(0f,1f,-.5f),
        Index.MIDDLE_TIP to Vector3(0f,1f,-.59f),Index.RING_PROXIMAL to Vector3(-.02f,1f,-.49f),
        Index.RING_TIP to Vector3(-.02f,1f,-.57f),Index.LITTLE_PROXIMAL to Vector3(-.035f,1f,-.49f))
    private fun read(points: Map<Index,Vector3>)=tracked(
        HandPose(points.map { (id,v) -> HandJoint(v,Quat.identity(),id) }),HandSide.RIGHT)

    @Test fun openPalmIsDistinguishedFromPinchAndExtendedIndex() {
        assertNotNull(read(joints)?.open)
        assertNull(read(joints+(Index.THUMB_TIP to joints.getValue(Index.INDEX_TIP)))?.open)
        assertNull(read(joints+(Index.MIDDLE_TIP to joints.getValue(Index.MIDDLE_PROXIMAL)))?.open)
        assertNull(read(joints+(Index.RING_TIP to joints.getValue(Index.RING_PROXIMAL)))?.open)
    }
    @Test fun incompleteSamplesDoNotThrowOrInventAPalm() {
        assertNull(read(joints-Index.WRIST))
        assertNull(read(joints-Index.LITTLE_PROXIMAL)?.open)
        assertNull(read(emptyMap()))
    }
}
