package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.garden.GardenPlacement
import com.bugworld.app.interaction.*
import com.pico.spatial.core.math.Vector3
import org.junit.Assert.*
import org.junit.Test

internal fun testPalm(point: HandPoint,side: HandSide=HandSide.RIGHT)=
    PalmSurface(side,point,HandPoint(0f,1f,0f),HandPoint(0f,0f,-1f),.07f)
internal fun HandInvitation.offer(point: HandPoint?,dt: Float)=
    update(if(point==null) emptyList() else listOf(testPalm(point)),null,dt)

class StageInvitationTest {
    @Test fun approachDoesNotConsumeLandingDwellAndLandedHandCanMove() {
        val invite=HandInvitation()
        val center=HandPoint(0f,1f,-.5f)
        repeat(8) { invite.offer(center,.1f) }
        invite.begin("chosen")
        repeat(90) { invite.offer(center,.1f) }
        assertEquals("chosen",invite.targetId)
        invite.landed("chosen")
        val moving=center+HandPoint(.08f,.02f,.1f)
        invite.offer(moving,.03f)
        assertEquals(moving,invite.surface?.center)
        repeat(25) { invite.offer(moving,.1f) }
        assertEquals("chosen",invite.targetId)
        repeat(6) { invite.offer(moving,.1f) }
        assertNull(invite.targetId)
        assertFalse(invite.canInvite)
    }

    @Test fun preferredPalmWinsAndLosingItNeverTransplantsTheResident() {
        val invite=HandInvitation()
        val right=testPalm(HandPoint(.3f,1f,-.5f))
        val left=testPalm(HandPoint(-.3f,1f,-.5f),HandSide.LEFT)
        repeat(10) { invite.update(listOf(right,left),HandSide.LEFT,.1f) }
        invite.begin("chosen"); invite.landed("chosen")
        assertEquals(HandSide.LEFT,invite.surface?.side)
        invite.update(listOf(right),HandSide.RIGHT,.1f)
        assertNull(invite.targetId)
        assertNull(invite.surface)
        invite.reset()
        repeat(10) { invite.update(listOf(left),HandSide.RIGHT,.1f) }
        assertTrue(invite.canInvite)
        assertEquals(HandSide.LEFT,invite.surface?.side)
    }

    @Test fun bothHandsFaceOutOfTheirPalmsAndFingersAloneCannotOfferBackOfHand() {
        val center=HandPoint(0f,1f,-.5f)
        val wrist=center+HandPoint(0f,0f,.05f)
        fun palm(side: HandSide): PalmSurface {
            val x=if(side==HandSide.RIGHT) .035f else -.035f
            return PalmSurface.from(side,center,wrist,center+HandPoint(x,0f,-.04f),
                center+HandPoint(-x,0f,-.04f))!!
        }
        for(side in HandSide.entries) assertEquals(1f,palm(side).normal.y,.001f)
        val invite=HandInvitation()
        val down=palm(HandSide.RIGHT).copy(normal=HandPoint(0f,-1f,0f))
        repeat(10) { invite.update(listOf(down),null,.1f) }
        assertFalse(invite.canInvite)
        assertNull(PalmSurface.from(HandSide.LEFT,center,wrist,center,center))
    }

    @Test fun tiltedTranslatedPalmAlignsFeetAndSpeciesForwardWithWearer() {
        val placement=GardenPlacement(2f,.2f,-1f,73f)
        val n=HandPoint(.3f,.9f,.2f).unit()!!
        val forward=HandPoint(0f,0f,-1f)
        val center=HandPoint(.2f,1.2f,-.4f)
        val raw=PalmSurface(HandSide.RIGHT,center,n,(forward-n*n.dot(forward)).unit()!!,.07f)
        val palm=raw.inSpace(placement::local)
        val eye=placement.local(HandPoint(.5f,1.6f,0f))
        val delta=eye-palm.center
        val direction=(delta-palm.normal*delta.dot(palm.normal)).unit()!!
        for(species in listOf(Species.BUTTERFLY,Species.BEETLE,Species.LADYBUG)) {
            val pose=palm.perch(species,eye,0f)
            val height=pose.point-palm.center
            assertTrue(height.dot(palm.normal) in .009f.. .014f)
            assertTrue(height.cross(palm.normal).dot(height.cross(palm.normal))<.000001f)
            val up=pose.orientation.rotateVector(Vector3(0f,1f,0f))
            assertEquals(1f,palm.normal.dot(HandPoint(up.x,up.y,up.z)),.001f)
            val front=if(species==Species.BUTTERFLY) Vector3(0f,0f,-1f) else Vector3(1f,0f,0f)
            val facing=pose.orientation.rotateVector(front)
            assertEquals(1f,direction.dot(HandPoint(facing.x,facing.y,facing.z)),.001f)
        }
    }
}
