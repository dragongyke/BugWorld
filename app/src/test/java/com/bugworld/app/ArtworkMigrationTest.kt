package com.bugworld.app

import com.bugworld.app.drawing.ArtworkMigration
import com.bugworld.app.drawing.PaintDocument
import org.junit.Assert.*
import org.junit.Test

class ArtworkMigrationTest {
    @Test fun changedAspectRatioKeepsAsymmetricStrokesAndClipsToNewSilhouette() {
        val old = IntArray(10*6)
        for (y in 2..3) for (x in 1..8) old[y*10+x] = if (x<5) RED else BLUE
        val target = IntArray(20*12) { if (it/20 in 3..8 && it%20 in 2..17) 1 else 0 }
        val pixels = ArtworkMigration.migrate(10,6,old,20,12,target,horizontalBody=true)
        assertEquals(RED,pixels[4*20+3]); assertEquals(BLUE,pixels[4*20+16])
        assertTrue(pixels.indices.filter { target[it]==0 }.all { pixels[it]==0 })
        assertEquals(RED,old[2*10+1]); assertEquals(BLUE,old[3*10+8])
    }

    @Test fun v1BeetleFrontAtTopMovesToTheRightBeforeShapeTransfer() {
        val old = IntArray(5*9)
        for (y in 1..7) for (x in 1..3) old[y*5+x] = if (y<4) RED else BLUE
        val pixels = ArtworkMigration.migrate(5,9,old,14,6,IntArray(84) { 1 },true,true)
        assertEquals(RED,pixels[3*14+12]); assertEquals(BLUE,pixels[3*14+1])
    }

    @Test fun transparentGapIsResolvedFromNearbyPaintInsteadOfDroppingTheStroke() {
        val old = intArrayOf(RED,0,BLUE,RED,0,BLUE)
        val result = ArtworkMigration.migrate(3,2,old,5,2,IntArray(10) { 1 },false)
        assertEquals(RED,result[0]); assertEquals(BLUE,result[4])
        assertTrue(result.all { it==RED || it==BLUE })
    }

    @Test fun emptySourceCreatesCleanPaperWithoutChangingInput() {
        val result = ArtworkMigration.migrate(2,2,IntArray(4),3,3,intArrayOf(0,0,0,0,1,0,0,0,0),true)
        assertEquals(PaintDocument.PAPER,result[4]); assertEquals(0,result[0])
    }
    companion object { private const val RED = -65536; private const val BLUE = -16776961 }
}
