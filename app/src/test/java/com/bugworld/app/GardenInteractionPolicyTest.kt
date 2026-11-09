package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.garden.InsectAction
import com.bugworld.app.garden.InsectAnimationController
import com.bugworld.app.interaction.*
import org.junit.Assert.*
import org.junit.Test

class GardenInteractionPolicyTest {
    @Test fun pinchRespondsForEverySpeciesAndSelectsEveryFlightCapableSpecies() {
        val expected=mapOf(Species.BUTTERFLY to GardenGestureResponse.RESPOND_AND_SELECT,
            Species.LADYBUG to GardenGestureResponse.RESPOND_AND_SELECT,
            Species.BEETLE to GardenGestureResponse.RESPOND_AND_SELECT,
            Species.CATERPILLAR to GardenGestureResponse.RESPOND,
            Species.ANT to GardenGestureResponse.RESPOND,
            Species.HONEYBEE to GardenGestureResponse.RESPOND_AND_SELECT,
            Species.DRAGONFLY to GardenGestureResponse.RESPOND_AND_SELECT,
            Species.GRASSHOPPER to GardenGestureResponse.RESPOND_AND_SELECT)
        for((species,response) in expected) {
            assertEquals(response,GardenInteractionPolicy.gesture(species,poke=false))
            assertEquals(InsectAction.TOUCH,InsectAnimationController(species)
                .update(.02f,reaction=GardenInteractionPolicy.REACTION).action)
        }
    }

    @Test fun pokeRespondsWithoutStartingAnInvitationForEverySpecies() {
        for(species in Species.entries)
            assertEquals(GardenGestureResponse.RESPOND,GardenInteractionPolicy.gesture(species,poke=true))
    }

    @Test fun birthRetirementVisitsAndTouchCooldownRejectNativeInput() {
        for(species in Species.entries) for(poke in listOf(false,true)) {
            assertEquals(GardenGestureResponse.IGNORE,GardenInteractionPolicy.gesture(species,poke,inBirth=true))
            assertEquals(GardenGestureResponse.IGNORE,GardenInteractionPolicy.gesture(species,poke,retiring=true))
            assertEquals(GardenGestureResponse.IGNORE,GardenInteractionPolicy.gesture(species,poke,visiting=true))
            assertEquals(GardenGestureResponse.IGNORE,GardenInteractionPolicy.gesture(species,poke,secondsSinceTouch=2.5f))
            assertNotEquals(GardenGestureResponse.IGNORE,GardenInteractionPolicy.gesture(species,poke,secondsSinceTouch=2.51f))
        }
    }

    @Test fun invitationRequiresStableHandAndAnAvailableExplicitlySelectedFlyer() {
        val invitation=HandInvitation()
        val selection=GardenSelection()
        val hand=HandPoint(0f,1f,-.5f)
        selection.select("chosen")
        repeat(4) { invitation.offer(hand,.1f) }
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.8f,invitation.canInvite))
        repeat(2) { invitation.offer(hand,.1f) }
        assertTrue(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.8f,invitation.canInvite))
        assertTrue(GardenInteractionPolicy.canInvite(Species.LADYBUG,.349f,invitation.canInvite))
        assertTrue(GardenInteractionPolicy.canInvite(Species.LADYBUG,.35f,invitation.canInvite))
        assertTrue(GardenInteractionPolicy.canInvite(Species.LADYBUG,.5f,invitation.canInvite))
        assertTrue(GardenInteractionPolicy.canInvite(Species.BEETLE,.1f,invitation.canInvite))
        assertFalse(GardenInteractionPolicy.canInvite(Species.CATERPILLAR,.1f,invitation.canInvite))
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,null,invitation.canInvite))
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,Float.NaN,invitation.canInvite))
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.2f,invitation.canInvite,inBirth=true))
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.2f,invitation.canInvite,retiring=true))
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.2f,invitation.canInvite,visiting=true))
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.2f,invitation.canInvite,responding=true))
        invitation.begin(selection.consume()!!)
        assertEquals("chosen",invitation.targetId)
        assertNull(selection.selected)
        assertFalse(GardenInteractionPolicy.canInvite(Species.BUTTERFLY,.2f,invitation.canInvite))
        invitation.offer(null,.1f)
        repeat(60) { invitation.offer(hand,.1f) }
        assertNull(invitation.targetId)
        assertNull(selection.selected)
    }

    @Test fun airborneAcknowledgementIsBriefAndDoesNotRotateGroundSpecies() {
        assertTrue(GardenInteractionPolicy.airborneResponseYaw(Species.BUTTERFLY,.4f)>0f)
        assertTrue(GardenInteractionPolicy.airborneResponseYaw(Species.LADYBUG,.4f)>0f)
        assertTrue(GardenInteractionPolicy.airborneResponseYaw(Species.BEETLE,.4f)>0f)
        assertEquals(0f,GardenInteractionPolicy.airborneResponseYaw(Species.CATERPILLAR,.4f),0f)
        assertEquals(0f,GardenInteractionPolicy.airborneResponseYaw(Species.BUTTERFLY,0f),0f)
        assertEquals(0f,GardenInteractionPolicy.airborneResponseYaw(Species.BUTTERFLY,1.8f),0f)
        assertEquals(0f,GardenInteractionPolicy.airborneResponseYaw(Species.BUTTERFLY,Float.NaN),0f)
    }
}
