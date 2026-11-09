package com.bugworld.app

import com.bugworld.app.garden.SceneRelease
import org.junit.Assert.*
import org.junit.Test

class SceneReleaseTest {
    @Test fun releaseWaitsForVisibleSceneAndPreparedResources() {
        val release=SceneRelease()
        val request=release.request("paint-a")
        assertNull(release.claim(false,true))
        assertNull(release.claim(true,false))
        assertEquals(request,release.claim(true,true))
        assertNull(release.claim(true,true))
        assertTrue(release.complete(request))
        assertNull(release.pending)
    }
    @Test fun repeatedClickIsOneRequestAndCancelledGenerationCannotCommit() {
        val release=SceneRelease()
        val a=release.request("a")
        assertEquals(a,release.request("a"))
        release.claim(true,true)
        release.cancel()
        val b=release.request("b")
        assertFalse(release.complete(a))
        assertEquals(b,release.pending)
        assertEquals(b,release.claim(true,true))
    }
    @Test fun failedPreparationCanRetryWithoutLosingPendingArtwork() {
        val release=SceneRelease()
        val a=release.request("a")
        release.claim(true,true)
        release.retry(a)
        assertEquals(a,release.claim(true,true))
    }
}
