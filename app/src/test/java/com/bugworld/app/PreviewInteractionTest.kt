package com.bugworld.app

import com.bugworld.app.spatial.PreviewInteraction
import com.bugworld.app.spatial.PreviewMotion
import com.bugworld.app.data.Species
import com.bugworld.app.garden.InsectAction
import com.pico.spatial.core.math.EulerAngles
import com.pico.spatial.core.math.Quat
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.abs

class PreviewInteractionTest {
    private fun same(a: Quat,b: Quat)=assertEquals(1f,abs(Quat.dot(a,b)),.0001f)

    @Test fun mixedWristRotationIncludingRollUsesSpatialAxesAndSurvivesRegrip() {
        val input=PreviewInteraction()
        val initial=input.orientation
        val hand=EulerAngles(15f,-55f,7f).toQuat()
        val twist=EulerAngles(-18f,70f,95f).toQuat()
        input.down(1,hand,1000,false)
        input.sample(1,twist*hand,1100); input.up(1,1200)
        val held=twist*initial
        same(held,input.orientation)
        assertEquals(0f,input.takeReaction(),0f)
        val other=EulerAngles(-90f,23f,47f).toQuat()
        input.down(2,other,2000,false)
        same(held,input.orientation)
        input.sample(2,other,2010) // Position changes are deliberately absent from this interface.
        same(held,input.orientation)
        val roll=EulerAngles(0f,0f,120f).toQuat()
        input.sample(2,roll*other,2100); input.up(2,2200)
        same(roll*held,input.orientation)
    }

    @Test fun pokeAndBriefPinchTapRespondWithoutOrientationChanges() {
        val input=PreviewInteraction(); val rest=input.orientation
        input.down(1,null,1000,true); assertTrue(input.takeReaction()>0f)
        input.sample(1,EulerAngles(33f,68f,9f).toQuat(),1080); input.up(1,1200)
        same(rest,input.orientation); assertEquals(0f,input.takeReaction(),0f)
        input.down(2,Quat.identity(),3200,false)
        input.sample(2,EulerAngles(0f,0f,1f).toQuat(),3250); input.up(2,3300)
        same(rest,input.orientation); assertTrue(input.takeReaction()>0f)
    }

    @Test fun independentPointerAndTrackingGapsCannotStealOrJump() {
        val input=PreviewInteraction(); val initial=input.orientation
        val roll=EulerAngles(0f,0f,45f).toQuat()
        input.down(1,Quat.identity(),1000,false)
        input.down(2,null,1010,true); input.up(2,1100)
        input.sample(1,roll,1110)
        val held=input.orientation
        same(roll*initial,held)
        input.sample(1,null,1120)
        input.sample(1,EulerAngles(80f,5f,20f).toQuat(),1130)
        same(held,input.orientation)
        input.sample(1,Quat.identity(),1900); same(held,input.orientation)
        input.releaseMissing(listOf(3))
        input.sample(1,roll,1950)
        same(held,input.orientation)
        assertEquals(0f,input.takeReaction(),0f)
        input.down(3,null,1960,true)
        assertTrue(input.takeReaction()>0f)
    }

    @Test fun cooldownAndHiddenIntervalDoNotLoseAnAcceptedTouch() {
        for(species in Species.entries) {
            val input=PreviewInteraction(); val motion=PreviewMotion(species)
            fun poke(at: Long) { input.down(1,null,at,true); input.up(1,at+10) }
            poke(1000); assertEquals(InsectAction.TOUCH,motion.update(.02f,input.takeReaction()>0f).action)
            poke(1300); assertEquals(0f,input.takeReaction(),0f)
            repeat(30) { motion.update(.02f,false) }
            input.cancel()
            poke(4600); val touched=motion.update(.05f,input.takeReaction()>0f)
            assertEquals(InsectAction.TOUCH,touched.action)
            assertEquals(0f,touched.progress,.001f)
        }
    }
}
