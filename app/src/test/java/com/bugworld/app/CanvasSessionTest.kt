package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.drawing.CanvasSession
import com.bugworld.app.drawing.PaintDocument
import org.junit.Assert.*
import org.junit.Test

class CanvasSessionTest {
    @Test fun editingEightSheetsRetainsTheirArtWhileBoundingInactiveUndoHistory() {
        val session=session()
        val docs=Species.entries.map { kind ->
            session.select(kind)
            session.current.document.also { it.fill(1,1,0xffab1234.toInt()) }
        }
        session.trimHistory(2L*8*8*4)
        assertEquals(2,docs.count { it.canUndo })
        assertTrue(session.current.document.canUndo)
        assertTrue(docs.all { it.pixels[9]==0xffab1234.toInt() })
    }
    private fun session() = CanvasSession(Species.entries.associateWith { PaintDocument(8,8,IntArray(64) { 1 }) })

    @Test fun newSessionStartsBlankEvenAfterPreviousSessionSavedAnEdit() {
        val previous=session()
        previous.current.document.fill(1,1,0xffab1234.toInt())
        previous.saved("saved-work")
        val next=session()
        assertNull(next.current.artworkId)
        assertEquals(PaintDocument.PAPER,next.current.document.pixels[9])
        assertFalse(next.current.document.canUndo)
    }
    @Test fun reopeningStudioClearsAllSessionSheetsButDoesNotMutatePreviousDocument() {
        val session=session()
        val original=session.current.document
        original.fill(1,1,0xffab1234.toInt()); session.saved("saved")
        session.select(Species.BEETLE)
        session.current.document.fill(1,1,0xffaabbcc.toInt())
        session.restart()
        assertEquals(Species.BUTTERFLY,session.species)
        assertEquals(0xffab1234.toInt(),original.pixels[9])
        for(species in Species.entries) {
            session.select(species)
            assertEquals(PaintDocument.PAPER,session.current.document.pixels[9])
            assertNull(session.current.artworkId)
            assertFalse(session.current.document.canUndo)
        }
    }
    @Test fun switchingReusesDocumentAndPreservesUndoAndEditIdentity() {
        val session=session()
        val document=session.current.document
        document.fill(1,1,0xffab1234.toInt())
        session.saved("saved-work")
        repeat(20) {
            session.select(Species.BEETLE)
            assertNull(session.current.artworkId)
            session.select(Species.BUTTERFLY)
            assertSame(document,session.current.document)
        }
        assertEquals("saved-work",session.current.artworkId)
        session.current.document.undo()
        assertEquals(PaintDocument.PAPER,document.pixels[9])
    }
    @Test fun freshPaperClearsOnlySelectedWorkAndItsUndo() {
        val session=session()
        val old=session.current.document
        old.fill(1,1,0xffab1234.toInt()); session.saved("old")
        session.select(Species.LADYBUG)
        val ladybug=session.current.document
        session.select(Species.BUTTERFLY); session.fresh()
        assertNotSame(old,session.current.document)
        assertEquals(PaintDocument.PAPER,session.current.document.pixels[9])
        assertFalse(session.current.document.canUndo)
        assertNull(session.current.artworkId)
        session.select(Species.LADYBUG); assertSame(ladybug,session.current.document)
    }
    @Test fun explicitAlbumEditSurvivesSwitchAndDeletionClearsHiddenIdentity() {
        val session=session()
        val restored=PaintDocument(8,8,IntArray(64) { 1 })
        restored.fill(1,1,0xffaabbcc.toInt())
        session.edit(Species.CATERPILLAR,restored,"album-work")
        assertSame(restored,session.current.document)
        session.select(Species.BUTTERFLY)
        session.deleted("album-work")
        session.select(Species.CATERPILLAR)
        assertSame(restored,session.current.document)
        assertNull(session.current.artworkId)
    }
    @Test fun blankCopyKeepsWaxMaterialWithoutSharingPaintOrHistory() {
        val original=PaintDocument(16,16,IntArray(256) { if(it%16==0) 0 else 1 })
        val copy=original.blankCopy()
        original.beginStroke(); original.stroke(5f,5f,10f,10f,3f,0xff6789ab.toInt(),false,false)
        assertEquals(PaintDocument.PAPER,copy.pixels[85])
        copy.beginStroke(); copy.stroke(5f,5f,10f,10f,3f,0xff6789ab.toInt(),false,false)
        assertArrayEquals(original.pixels,copy.pixels)
        copy.undo()
        assertNotEquals(original.pixels[85],copy.pixels[85])
        assertEquals(0,copy.pixels[0])
    }
}
