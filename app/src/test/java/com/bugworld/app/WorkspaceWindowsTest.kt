package com.bugworld.app

import org.junit.Assert.*
import org.junit.Test

class WorkspaceWindowsTest {
    @Test fun recreationDoesNotTurnAnOpenAlbumIntoAUserClose() {
        val windows = WorkspaceWindows(setOf("paper", "album"))
        windows.detached("album", closedByUser = false)
        windows.beginStage()
        assertEquals(setOf("paper", "album"), windows.stageReady())
        windows.beginReturn()
        assertEquals(setOf("paper", "album"), windows.finishReturn("paper"))
        windows.detached("album", closedByUser = true)
        windows.beginStage()
        assertEquals(setOf("paper"), windows.stageReady())
    }
    @Test fun returningFromAlbumOnlyAlwaysRestoresPaperButDoesNotInventAnAlbum() {
        for (open in listOf(emptySet(), setOf("album"))) {
            val windows = WorkspaceWindows(open)
            windows.beginStage()
            assertEquals(open, windows.stageReady())
            windows.beginReturn()
            assertEquals(open + "paper", windows.finishReturn("paper"))
        }
    }
    @Test fun failedStageCloseCanRetryWithoutLosingWindows() {
        for(ready in listOf(false,true)) {
            val windows=WorkspaceWindows(setOf("paper","album"))
            windows.beginStage(); if(ready) windows.stageReady()
            val before=windows.phase
            assertTrue(windows.beginReturn())
            windows.returnFailed()
            assertEquals(before,windows.phase)
            assertTrue(windows.beginReturn())
            assertEquals(setOf("paper","album"),windows.finishReturn("paper"))
        }
    }
    @Test fun windowsStayVisibleUntilTheActualStageIsReady() {
        val windows=WorkspaceWindows(setOf("paper","tools"))
        assertTrue(windows.beginStage())
        assertFalse(windows.beginStage())
        assertEquals(setOf("paper","tools"),windows.openIds)
        assertEquals(setOf("paper","tools"),windows.stageReady())
        assertTrue(windows.stageReady().isEmpty())
    }
    @Test fun refusedStagePreservesWorkspaceAndAllowsRetry() {
        val windows=WorkspaceWindows(setOf("paper","tools"))
        windows.beginStage()
        assertTrue(windows.stageRejected())
        assertEquals(setOf("paper","tools"),windows.openIds)
        assertTrue(windows.beginStage())
    }
    @Test fun stageDestructionDoesNotLoseTheSavedWindowSet() {
        val windows=WorkspaceWindows(setOf("paper","bar","album"))
        windows.beginStage(); windows.stageReady()
        windows.detached("album"); windows.detached("bar")
        assertTrue(windows.beginReturn())
        assertEquals(setOf("paper","bar","album"),windows.finishReturn("paper"))
        assertFalse(windows.beginReturn())
    }
    @Test fun closedToolsAreNotReopenedWhenReturningFromStage() {
        val windows=WorkspaceWindows(setOf("paper","bar","tools"))
        windows.detached("tools"); windows.beginStage(); windows.stageReady()
        windows.beginReturn()
        assertEquals(setOf("paper","bar"),windows.finishReturn("paper"))
    }
    @Test fun closeDuringOpeningIsNotMistakenForStageMinimization() {
        val windows=WorkspaceWindows(setOf("paper","album"))
        windows.beginStage(); windows.closed("album")
        assertEquals(setOf("paper"),windows.stageReady())
        windows.beginReturn(); assertEquals(setOf("paper"),windows.finishReturn("paper"))
    }
    @Test fun nativeDisposalWhileStageLoadsPreservesAllWindows() {
        val windows=WorkspaceWindows(setOf("paper","bar","tools"))
        windows.beginStage(); windows.detached("paper"); windows.detached("bar"); windows.detached("tools")
        assertEquals(setOf("paper","bar","tools"),windows.stageReady())
    }
    @Test fun lateWindowAttachmentIsPreservedAcrossStageDisposal() {
        val windows=WorkspaceWindows(setOf("paper"))
        windows.beginStage()
        // A pending native open can attach after Stage launch captured the workspace.
        windows.opened("tools")
        windows.detached("tools")
        assertEquals(setOf("paper","tools"),windows.stageReady())
        windows.beginReturn()
        assertEquals(setOf("paper","tools"),windows.finishReturn("paper"))
    }
    @Test fun windowsOpenedAndClosedAcrossRepeatedStageVisitsKeepUserChoices() {
        val windows=WorkspaceWindows(setOf("paper","tools","album"))
        repeat(3) {
            windows.beginStage(); windows.stageReady()
            windows.detached("paper"); windows.detached("tools"); windows.detached("album")
            windows.beginReturn()
            assertEquals(setOf("paper","tools","album"),windows.finishReturn("paper"))
        }
        windows.closed("tools")
        windows.beginStage(); windows.stageReady(); windows.beginReturn()
        assertEquals(setOf("paper","album"),windows.finishReturn("paper"))
    }
}
