package com.bugworld.app

import com.bugworld.app.interaction.TrackingLifecycle
import org.junit.Assert.*
import org.junit.Test

class TrackingLifecycleTest {
    @Test fun deniedHandPermissionStillTracksHeadAndCanBeGrantedLater() {
        val events=mutableListOf<String>()
        val tracking=TrackingLifecycle({events+="head+"},{events+="head-"},
            {events+="hands+"},{events+="hands-"})
        tracking.update(active=true,handPermissionGranted=false)
        assertTrue(tracking.headActive)
        assertFalse(tracking.handsActive)
        tracking.update(active=true,handPermissionGranted=true)
        tracking.update(active=true,handPermissionGranted=true)
        assertEquals(listOf("head+","hands+"),events)
    }

    @Test fun permissionRevocationStopsHandsWithoutMovingTheGarden() {
        val events=mutableListOf<String>()
        val tracking=TrackingLifecycle({events+="head+"},{events+="head-"},
            {events+="hands+"},{events+="hands-"})
        tracking.update(true,true)
        tracking.update(true,false)
        assertTrue(tracking.headActive)
        assertFalse(tracking.handsActive)
        assertEquals(listOf("head+","hands+","hands-"),events)
        tracking.update(false,false)
        tracking.update(false,false)
        assertEquals("head-",events.last())
        assertEquals(4,events.size)
    }

    @Test fun backgroundingStopsBothAndResumeRespectsCurrentPermission() {
        val events=mutableListOf<String>()
        val tracking=TrackingLifecycle({events+="head+"},{events+="head-"},
            {events+="hands+"},{events+="hands-"})
        tracking.update(true,true)
        tracking.update(false,true)
        assertFalse(tracking.headActive)
        assertFalse(tracking.handsActive)
        tracking.update(true,false)
        assertEquals(listOf("head+","hands+","hands-","head-","head+"),events)
    }

    @Test fun failedHandStartIsCleanedUpAndLeavesHeadTrackingAvailable() {
        val events=mutableListOf<String>()
        val tracking=TrackingLifecycle({events+="head+"},{events+="head-"},
            {events+="hands+";throw SecurityException("permission revoked")},{events+="hands-"})
        assertThrows(SecurityException::class.java) {tracking.update(true,true)}
        assertTrue(tracking.headActive)
        assertFalse(tracking.handsActive)
        tracking.update(false,false)
        assertEquals(listOf("head+","hands+","hands-","head-"),events)
    }
}
