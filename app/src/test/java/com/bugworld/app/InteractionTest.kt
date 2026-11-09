package com.bugworld.app

import com.bugworld.app.interaction.*
import com.bugworld.app.garden.Population
import org.junit.Assert.*
import org.junit.Test

class InteractionTest {
    @Test fun retirementFinishesBeforeNextArrivalAndDeletedPendingDoesNotReturn() {
        val population=Population(10)
        population.tick((1..10).map(Int::toString),1f)
        population.tick((2..11).map(Int::toString),.1f)
        assertEquals(10,population.entries.size)
        assertFalse(population.entries.containsKey("11"))
        population.tick((2..10).map(Int::toString),2f)
        assertEquals(9,population.entries.size)
        assertFalse(population.entries.containsKey("11"))
        population.tick((2..11).map(Int::toString),.1f)
        assertEquals(10,population.entries.size)
        assertTrue(population.entries.containsKey("11"))
    }
    @Test fun handMustBeStableAndTrackingLossEndsInvitation() {
        val invitation=HandInvitation()
        val hand=HandPoint(0f,1f,-.5f)
        invitation.offer(hand,.2f)
        assertFalse(invitation.canInvite)
        repeat(8) { invitation.offer(hand,.1f) }
        assertTrue(invitation.canInvite)
        invitation.begin("butterfly")
        assertEquals("butterfly",invitation.targetId)
        invitation.offer(null,.1f)
        assertNull(invitation.targetId)
    }
    @Test fun fastMovementAndInvalidCoordinatesCannotAttract() {
        val invitation=HandInvitation()
        repeat(10) { invitation.offer(HandPoint(it.toFloat(),1f,-.5f),.1f) }
        assertFalse(invitation.canInvite)
        invitation.offer(HandPoint(Float.NaN,0f,0f),1f)
        assertFalse(invitation.canInvite)
        invitation.reset()
        assertNull(invitation.surface)
    }
}
