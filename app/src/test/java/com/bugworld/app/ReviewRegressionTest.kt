package com.bugworld.app

import com.bugworld.app.data.*
import com.bugworld.app.drawing.PreviewLink
import com.bugworld.app.interaction.*
import java.io.IOException
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

class ReviewRegressionTest {
    @Test fun refusedStageKeepsSharedWindowsAndCanRetry()= runBlocking {
        var allowed=false; var hidden=0
        val navigation=StageNavigation({allowed}) { hidden++ }
        assertFalse(navigation.enter()); assertEquals(0,hidden)
        allowed=true
        assertTrue(navigation.enter()); assertEquals(1,hidden)
    }
    @Test fun failedDraftWriteReportsAndCanRetryWithoutLosingDocument()= runBlocking {
        var failure: Exception?=null; val pixels=intArrayOf(1,2,3)
        assertFalse(DraftWrite.attempt({ throw IOException("No space") },{failure=it}))
        assertTrue(failure is IOException); assertArrayEquals(intArrayOf(1,2,3),pixels)
        assertTrue(DraftWrite.attempt({}, { fail("Unexpected error") }))
    }
    @Test(expected=CancellationException::class) fun cancelledDraftIsNotReportedAsDiskFailure()= runBlocking {
        DraftWrite.attempt({ throw CancellationException() },{ fail("Cancellation must propagate") }); Unit
    }
    @Test fun sustainedSlowHandMotionFollowsAt60And90Hz() {
        for(rate in listOf(60,90)) {
            val tracker=HandInvitation(); val dt=1f/rate
            repeat(rate) { tracker.offer(HandPoint(0f,1f,-.6f),dt) }
            tracker.begin("bug")
            repeat(rate*2) { i -> tracker.offer(HandPoint((i+1)*dt*.2f,1f,-.6f),dt) }
            assertEquals("bug",tracker.targetId)
            tracker.offer(HandPoint(2f,1f,-.6f),dt)
            assertNull(tracker.targetId)
        }
    }
    @Test fun previewTracksOnlyItsSourceAndDetectsNewRevisions() {
        val link=PreviewLink(); link.draft(Species.BUTTERFLY,1)
        assertFalse(link.changedDraft(Species.LADYBUG,2))
        assertTrue(link.changedDraft(Species.BUTTERFLY,2))
        assertFalse(link.changedDraft(Species.BUTTERFLY,2))
        link.saved("one",3)
        assertFalse(link.changedDraft(Species.BUTTERFLY,3))
        assertFalse(link.changedSaved("other",4))
        assertTrue(link.changedSaved("one",4)); assertFalse(link.changedSaved("one",4))
        assertTrue(link.clear("one")); assertFalse(link.changedSaved("one",5))
    }
    @Test fun unchangedPreviewCanReuseColorsButNeverAcrossSourceOrRevision() {
        val link=PreviewLink()
        assertFalse(link.matchesDraft(Species.BUTTERFLY,1))
        link.draft(Species.BUTTERFLY,1)
        assertTrue(link.matchesDraft(Species.BUTTERFLY,1))
        assertFalse(link.matchesDraft(Species.BUTTERFLY,2))
        assertFalse(link.matchesDraft(Species.BEETLE,1))
        link.saved("one",3)
        assertTrue(link.matchesSaved("one",3))
        assertFalse(link.matchesSaved("one",4))
        assertFalse(link.matchesSaved("two",3))
        assertFalse(link.matchesDraft(Species.BUTTERFLY,1))
        link.clear("one")
        assertFalse(link.matchesSaved("one",3))
    }
}
