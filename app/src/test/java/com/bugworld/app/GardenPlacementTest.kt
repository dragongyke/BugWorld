package com.bugworld.app
import com.bugworld.app.garden.GardenPlacement
import com.bugworld.app.interaction.*
import org.junit.Assert.*
import org.junit.Test

class GardenPlacementTest {
    @Test fun relocatedGardenAndTrackedHandUseTheSameFrame() {
        for(yaw in listOf(0f,30f,90f,-179f)) {
            val entry=GardenPlacement(1.3f,-.25f,-2f,yaw)
            val local=HandPoint(.4f,.8f,-.6f)
            assertTrue(entry.local(entry.world(local)).distance(local)<.00001f)
        }
        assertEquals(HandPoint(-1f,0f,0f),GardenPlacement(yaw=90f).world(HandPoint(0f,0f,-1f)).let {
            HandPoint(kotlin.math.round(it.x),it.y,kotlin.math.round(it.z))
        })
    }
    @Test fun onlyExplicitSelectionCanBeConsumedAndNeverSelectsAnotherWork() {
        val target=GardenSelection()
        target.tick(1f,setOf("a","b"));assertNull(target.consume())
        target.select("a");target.tick(.1f,setOf("a","b"));assertEquals("a",target.consume())
        assertNull(target.consume())
        target.select("a");target.tick(.1f,setOf("b"));assertNull(target.selected)
        target.select("b");target.tick(13f,setOf("b"));assertNull(target.selected)
    }
}
