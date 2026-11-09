package com.bugworld.app
import com.bugworld.app.interaction.*
import org.junit.Assert.*
import org.junit.Test

class VisitMotionTest {
    @Test fun endingVisitDuringReactionStillReturnsContinuouslyToItsRealRoute() {
        val motion=VisitMotion()
        val home=HandPoint(0f,1f,-1.5f);val hand=HandPoint(0f,1f,-.5f)
        motion.target(hand,hand,home,false)
        assertEquals(hand,motion.target(null,hand,home,true))
        assertTrue(motion.returning)
        repeat(100) { motion.target(null,hand,home,true) }
        assertTrue(motion.returning)
        assertEquals(home,motion.target(null,hand,home,false))
        assertTrue(motion.returning)
        motion.target(null,home,home,false)
        assertFalse(motion.returning)
    }
}
