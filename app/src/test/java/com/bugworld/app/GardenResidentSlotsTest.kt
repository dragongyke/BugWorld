package com.bugworld.app

import com.bugworld.app.data.Artwork
import com.bugworld.app.data.Species
import com.bugworld.app.garden.*
import com.bugworld.app.interaction.distance
import kotlin.math.abs
import org.junit.Assert.*
import org.junit.Test

class GardenResidentSlotsTest {
    private fun work(id: String,s: Species)=Artwork(id,s,1,1,1,3)

    @Test fun firstArrivalUsesAForwardPerchAndUsesOtherRoutesBeforeSharing() {
        for(s in Species.entries) {
            val count=ApprovedGardenRoutes.count(s)
            val works=(1..10).map { work("art-$it",s) }
            val first=GardenResidentSlots.plan(works.take(1),"art-1").single()
            val spawn=ApprovedGardenRoutes.arrivalPose(s,first.slot).point
            if (s == Species.ANT) {
                // Ants now spawn on the exposed bank or bark, outside the forward leaf area.
                assertTrue(spawn.y < .18f && kotlin.math.hypot(spawn.x, spawn.z) > 4f)
                assertTrue(ApprovedGardenRoutes.arrivalPose(s, 1).point.y > .5f)
            } else {
                assertTrue("$s forward spawn $spawn",spawn.z<-.5f && abs(spawn.x)<-spawn.z*.6f)
            }
            val placements=GardenResidentSlots.plan(works,"art-10")
            assertEquals("art-10",placements.first().work.id)
            // Each release rebuilds Stage. Its route must match the available route at that time.
            for(k in 1..10) {
                val cold=GardenResidentSlots.plan(works.take(k),works[k-1].id)
                assertEquals((k-1)%count,cold.first().slot)
                for(row in cold) assertEquals(works.indexOf(row.work)%count,row.slot)
            }
            val sizes=placements.groupingBy { it.slot }.eachCount().values
            assertTrue(sizes.max()-sizes.min()<=1)
        }
    }

    @Test fun aReplacementUsesEvictedResidentsCapacityWithoutMovingVisibleWorks() {
        val old=(0 until 10).map { work("old-$it",Species.CATERPILLAR) }
        val occupied=GardenResidentSlots.plan(old,null).associate { it.work.id to it.slot }
        val incoming=work("new",Species.CATERPILLAR)
        val planned=GardenResidentSlots.plan(old+incoming,incoming.id,occupied)
        assertEquals(incoming.id,planned.first().work.id)
        assertEquals(occupied.getValue(old.first().id),planned.first().slot)
        for(p in planned.drop(1)) assertEquals(occupied.getValue(p.work.id),p.slot)
        val rerelease=GardenResidentSlots.plan(old+old[3],old[3].id,occupied)
        assertEquals(10,rerelease.size)
        assertEquals(occupied.getValue(old[3].id),rerelease.first().slot)
    }

    @Test fun tenSameSpeciesResidentsAllLeaveTheirOwnSpawnAndKeepSpacingDuringVisitsAndBirths() {
        for(s in Species.entries) {
            val works=(0 until 10).map { work("same-$it",s) }
            val plans=GardenResidentSlots.plan(works,works.first().id)
            val lanes=List(ApprovedGardenRoutes.count(s)) { slot -> GardenRouteTraffic(s, slot) }
            val joined=linkedSetOf<String>()
            var visitPositions=emptyMap<String,Float>()
            for(frame in 0..2500) {
                // Hold one route for its birth and later through an outbound visit and return.
                for((i,lane) in lanes.withIndex()) {
                    lane.held=i==0 && (frame in 1..55 || frame in 800..950)
                    lane.advance(.05f)
                }
                for((w,i) in plans) if(w.id !in joined && lanes[i].admit(w.id)) {
                    assertEquals(0f,lanes[i].routeTime(w.id),0f)
                    joined.add(w.id)
                }
                if(frame==799) visitPositions=plans.filter { it.slot==0 }.associate { it.work.id to lanes[0].routeTime(it.work.id) }
                if(frame in 800..950) for((id,start) in visitPositions) assertEquals(start,lanes[0].routeTime(id),0f)
                if(frame==798) assertEquals("$s all ten should depart",10,joined.size)
                if(frame%10==0) for((i,lane) in lanes.withIndex()) {
                    val points=plans.filter { it.slot==i && it.work.id in joined }.map {
                        ApprovedGardenRoutes.pose(s,i,lane.routeTime(it.work.id)).point
                    }
                    for(a in points.indices) for(b in 0 until a) assertTrue("$s/$i overlapped",points[a].distance(points[b])>.48f*ApprovedGardenRoutes.stageScale(s)+.01f)
                }
            }
        }
    }

    @Test fun retirementFreesAPhaseOnlyAtTheNextPassThroughItsSpawn() {
        val lane=GardenRouteTraffic(Species.CATERPILLAR)
        repeat(5) { id ->
            var joined=false
            repeat(160) { if(!joined) { lane.advance(.05f); joined=lane.admit(id.toString()) } }
            assertTrue(joined)
        }
        lane.advance(.05f)
        assertFalse(lane.admit("new"))
        lane.depart("2")
        assertFalse(lane.admit("new"))
        var admitted=false
        repeat(685) { if(!admitted) { lane.advance(.05f); admitted=lane.admit("new") } }
        assertTrue(admitted)
        assertEquals(0f,lane.routeTime("new"),0f)
    }
}
