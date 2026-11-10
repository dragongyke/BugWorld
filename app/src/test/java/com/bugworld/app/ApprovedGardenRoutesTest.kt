package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.garden.ApprovedGardenRoutes as Routes
import com.bugworld.app.interaction.distance
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class ApprovedGardenRoutesTest {
    private val span=Species.entries.associateWith { .48f*Routes.stageScale(it) }

    @Test fun eachSpeciesHasSeparateSpawnsAndReturnsToItsExactStartingPoint() {
        for(s in Species.entries) {
            val starts=(0 until Routes.count(s)).map { Routes.arrivalPose(s,it).point }
            assertTrue(starts.size in 2..3)
            for(i in starts.indices) {
                val start=starts[i]
                for(j in 0 until i) assertTrue(start.distance(starts[j])>.5f)
                val period=Routes.period(s,i)
                assertEquals(start,Routes.pose(s,i,period).point)
                assertTrue(start.distance(Routes.pose(s,i,period-.001f).point)<.003f)
                assertTrue(start.distance(Routes.pose(s,i,period+.001f).point)<.003f)
            }
        }
    }

    @Test fun sameSpeciesLanesHaveDistinctLoopDurations() {
        for (species in Species.entries) {
            val periods = List(Routes.count(species)) { Routes.period(species, it) }.sorted()
            assertTrue(periods.zipWithNext().all { (a, b) -> b - a > 1f })
        }
    }

    @Test fun speciesUseTheirOwnOrderedActivitiesAndRelativeDurations() {
        for(s in Species.entries) for(i in 0 until Routes.count(s)) {
            val period=Routes.period(s,i)
            val poses=(0 until 1000).map { Routes.pose(s,i,it*period/1000) }
            if(s==Species.CATERPILLAR) {
                assertTrue(poses.all { it.moving && !it.airborne })
                continue
            }
            if(s==Species.ANT) {
                assertTrue(poses.none { it.airborne || it.hopPhase!=null })
                assertTrue(poses.any { it.moving } && poses.any { !it.moving })
                continue
            }
            if(s==Species.GRASSHOPPER) {
                val starts=poses.indices.filter { poses[it].hopPhase!=null && poses.getOrNull(it-1)?.hopPhase==null }
                assertEquals(2,starts.size)
                for(j in starts) {
                    var k=j
                    while(k+1<poses.size && poses[k+1].hopPhase!=null) {
                        assertTrue(poses[k].airborne && poses[k+1].hopPhase!!>=poses[k].hopPhase!!)
                        k++
                    }
                    assertTrue(poses[k].point.distance(poses[j].point)>.1f && !poses[k+1].airborne)
                }
                val wingFlight=poses.indexOfFirst { it.airborne && it.hopPhase==null }
                assertTrue(wingFlight>starts.last() && wingFlight>poses.size*.78f)
                continue
            }
            val walking=poses.indexOfFirst { it.moving && !it.airborne }
            val opening=poses.indexOfFirst { it.airborne }
            val flight=poses.indexOfFirst { it.airborne && it.moving }
            assertTrue(!poses.first().moving && walking>0 && walking<opening && opening<flight)
            assertTrue(poses[walking].point.distance(poses[opening].point)>.05f)
            assertEquals(poses[opening].point,poses[flight-1].point)
            if(s in setOf(Species.BUTTERFLY,Species.DRAGONFLY,Species.HONEYBEE)) {
                assertTrue(1000-flight>4*(opening-walking))
                if(s!=Species.BUTTERFLY) assertTrue(poses.drop(flight).any { it.airborne && !it.moving })
            }
            else assertTrue(opening-walking>2*(1000-flight))
            if(s==Species.BEETLE) assertTrue(poses.all { it.point.x<-.4f })
        }
    }

    @Test fun everyPhaseSeatHasClearanceAcrossTheFullLoopIncludingOpeningAndLanding() {
        for(s in Species.entries) for(i in 0 until Routes.count(s)) {
            val period=Routes.period(s,i)
            val seats=Routes.seats(s)
            val points=(0 until 2000).map { Routes.pose(s,i,it*period/2000).point }
            for(k in 1 until seats) for(j in points.indices) {
                val d=points[j].distance(points[(j+k*points.size/seats)%points.size])
                assertTrue("$s/$i seats $k clearance $d",d>span.getValue(s)+.02f)
            }
        }
    }

    @Test fun differentRoutesKeepClearAtIndependentPhases() {
        val paths=Species.entries.flatMap { s -> (0 until Routes.count(s)).map { i ->
            s to (0 until 240).map { Routes.pose(s,i,it*Routes.period(s,i)/240).point }
        } }
        for(a in paths.indices) for(b in 0 until a) {
            val (sa,pa)=paths[a]; val (sb,pb)=paths[b]
            val minimum=(span.getValue(sa)+span.getValue(sb))*.5f+.01f
            for(p in pa) for(q in pb) {
                val d=p.distance(q)
                assertTrue("Paths $a / $b come within $d m",d>minimum)
            }
        }
    }

    @Test fun densePosesStayContinuousFiniteAndInsideTheGarden() {
        for(s in Species.entries) for(i in 0 until Routes.count(s)) {
            var previous=Routes.arrivalPose(s,i).point
            for(j in 1..2400) {
                val pose=Routes.pose(s,i,j*.02f)
                val p=pose.point
                assertTrue(p.finite && pose.yaw.isFinite() && pose.pitch.isFinite() && pose.roll.isFinite())
                assertTrue("$s/$i at $p",hypot(p.x,p.z) in .6f..5.5f && p.y in -.1f..3.7f)
                assertTrue("$s/$i jumps at ${j*.02f}",previous.distance(p)<.025f)
                previous=p
            }
        }
    }

    @Test fun nativeModelForwardAxisFollowsContactTravel() {
        for(s in Species.entries) for(i in 0 until Routes.count(s)) {
            val t=when(s) {
                Species.BUTTERFLY -> 2f
                Species.DRAGONFLY, Species.HONEYBEE -> .86f
                else -> 8f
            }
            val routeTime = t * Routes.period(s, i) / Routes.period(s, 0)
            val pose=Routes.pose(s,i,routeTime)
            val target=Routes.pose(s,i,routeTime+.02f).point
            val d=target-pose.point
            val pitch=pose.pitch*PI/180; val yaw=pose.yaw*PI/180; val roll=pose.roll*PI/180
            val forward=if(s==Species.BUTTERFLY)
                doubleArrayOf(-sin(yaw)*cos(pitch),sin(pitch),-cos(yaw)*cos(pitch))
            else doubleArrayOf(cos(yaw)*cos(roll)+sin(yaw)*sin(pitch)*sin(roll),
                cos(pitch)*sin(roll),-sin(yaw)*cos(roll)+cos(yaw)*sin(pitch)*sin(roll))
            val dot=(forward[0]*d.x+forward[1]*d.y+forward[2]*d.z)/sqrt(d.dot(d)).toDouble()
            assertTrue("$s/$i native alignment $dot",dot>.78)
        }
    }
}
