package com.bugworld.app

import com.bugworld.app.drawing.PaintDocument
import com.bugworld.app.drawing.PaintGesture
import org.junit.Assert.*
import org.junit.Test

class PaintDocumentTest {
    @Test fun approvedOffCentreButterflyAxisMirrorsFillAndWaxToItsOtherWing() {
        val regions=IntArray(8*8) { if(it%8==1) 1 else if(it%8==3) 2 else 0 }
        val doc=PaintDocument(8,8,regions,mirrorAxisX=2f)
        doc.fill(1,3,RED,true)
        assertEquals(RED,doc.pixels[3*8+3])
        doc.undo(); doc.beginStroke()
        doc.stroke(1f,3f,1f,3f,1f,RED,true,false)
        assertEquals(doc.pixels[3*8+1],doc.pixels[3*8+3])
        assertNotEquals(PaintDocument.PAPER,doc.pixels[3*8+3])
    }

    @Test fun lockedMarkStaysTransparentDuringFillCrayonAndErase() {
        val regions=IntArray(64) { 1 }.apply { this[27]=0 }
        val doc=PaintDocument(8,8,regions)
        doc.fill(1,1,RED); doc.beginStroke()
        doc.stroke(1f,3f,6f,3f,3f,BLUE,false,false)
        assertEquals(0,doc.pixels[27])
        doc.beginStroke(); doc.stroke(1f,3f,6f,3f,3f,BLUE,false,true)
        assertEquals(0,doc.pixels[27])
    }

    @Test fun mirroredFillIsOneUndoableAction() {
        val doc=document()
        doc.fill(1,1,RED,mirror=true)
        assertEquals(RED,doc.pixels[9]); assertEquals(RED,doc.pixels[14])
        doc.undo()
        assertEquals(PaintDocument.PAPER,doc.pixels[9]); assertEquals(PaintDocument.PAPER,doc.pixels[14])
        assertFalse(doc.canUndo)
    }
    private fun document() = PaintDocument(8, 8, IntArray(64) { if (it % 8 < 4) 1 else 2 })
    @Test fun fillRespectsTemplateRegionAndUndoRedo() {
        val doc = document()
        doc.fill(1, 1, RED)
        assertEquals(RED, doc.pixels[9])
        assertEquals(PaintDocument.PAPER, doc.pixels[15])
        doc.undo()
        assertEquals(PaintDocument.PAPER, doc.pixels[9])
        doc.redo()
        assertEquals(RED, doc.pixels[9])
    }
    @Test fun symmetryAndEraseRemainInsideSilhouette() {
        val mask = IntArray(64) { if (it / 8 in 2..5) 1 else 0 }
        val doc = PaintDocument(8, 8, mask)
        doc.beginStroke()
        doc.stroke(1f, 3f, 1f, 3f, 1f, RED, true, false)
        assertNotEquals(PaintDocument.PAPER, doc.pixels[3 * 8 + 1])
        assertEquals(doc.pixels[3 * 8 + 1], doc.pixels[3 * 8 + 6])
        assertEquals(0, doc.pixels[1])
        doc.beginStroke()
        doc.stroke(1f, 3f, 1f, 3f, 1f, RED, true, true)
        assertEquals(PaintDocument.PAPER, doc.pixels[3 * 8 + 1])
    }
    @Test fun newEditClearsRedoAndLoadedPixelsAreCopied() {
        val doc = document()
        val incoming = IntArray(64) { RED }
        doc.restore(incoming)
        incoming[0] = 0
        assertEquals(RED, doc.pixels[0])
        doc.fill(1, 1, BLUE)
        doc.undo()
        doc.fill(1, 1, RED)
        assertFalse(doc.canRedo)
    }

    @Test fun onePassLeavesPaperBetweenWaxGrains() {
        val doc = paper()
        pass(doc)
        val centre = sampleCentre(doc)
        assertTrue("A crayon pass must leave paper valleys", centre.count { it == PaintDocument.PAPER } > centre.size / 50)
        assertTrue("A crayon pass must deposit visible pigment", centre.count { darkness(it) > 0.15 } > centre.size / 4)
        assertTrue("One pass must not become a flat opaque stripe", centre.map(::darkness).average() < 0.85)
    }

    @Test fun repeatedPassesAccumulateInsteadOfBeingOpaqueImmediately() {
        val doc = paper()
        pass(doc)
        val first = sampleCentre(doc).map(::darkness).average()
        repeat(3) { pass(doc) }
        val layered = sampleCentre(doc).map(::darkness).average()
        assertTrue("Layering must visibly add wax: $first -> $layered", layered > first + 0.10)
        assertTrue("Paper relief must survive layered wax", sampleCentre(doc).any { darkness(it) < 0.1 })
    }

    @Test fun splittingOneGestureIntoManyEventsDoesNotChangeItsColour() {
        val single = paper()
        val split = paper()
        pass(single)
        split.beginStroke()
        for (x in 24 until 232) split.stroke(x.toFloat(),64f,x+1f,64f,16f,RED,false,false)
        assertArrayEquals(single.pixels,split.pixels)
    }

    @Test fun duplicateStationaryEventsDoNotDepositMoreWax() {
        val doc = paper()
        doc.beginStroke()
        doc.stroke(80f,64f,80f,64f,16f,RED,false,false)
        val first = doc.pixels.copyOf()
        repeat(12) { doc.stroke(80f,64f,80f,64f,16f,RED,false,false) }
        assertArrayEquals(first,doc.pixels)
    }

    @Test fun paperTextureAndAccumulationSurviveUndoRedoAndReload() {
        val doc = paper()
        pass(doc)
        val first = doc.pixels.copyOf()
        pass(doc)
        val second = doc.pixels.copyOf()
        doc.undo()
        assertArrayEquals(first,doc.pixels)
        doc.redo()
        assertArrayEquals(second,doc.pixels)
        val reloaded = paper()
        reloaded.restore(second)
        pass(doc); pass(reloaded)
        assertArrayEquals(doc.pixels,reloaded.pixels)
        doc.undo(); doc.undo()
        assertArrayEquals(first,doc.pixels)
    }

    @Test fun mirrorDoesNotDoubleDepositAtTheCentreSeam() {
        val plain = paper()
        val mirrored = paper()
        plain.beginStroke(); mirrored.beginStroke()
        plain.stroke(127.5f,20f,127.5f,108f,18f,RED,false,false)
        mirrored.stroke(127.5f,20f,127.5f,108f,18f,RED,true,false)
        for (y in 30..98) {
            val left = mirrored.pixels[y*256+127]
            assertEquals(left,mirrored.pixels[y*256+128])
            assertEquals("Mirror centre must receive one deposit",plain.pixels[y*256+127],left)
        }
    }

    @Test fun continuousStrokeCoversItsWholeLengthInsideAnArbitrarySizedMask() {
        val width = 213
        val height = 87
        val mask = IntArray(width*height) { if (it%width in 10..202 && it/width in 15..71) 1 else 0 }
        val doc = PaintDocument(width,height,mask)
        doc.beginStroke()
        doc.stroke(-30f,43f,260f,43f,12f,RED,false,false)
        for (x in 12..200) assertTrue((35..51).any { y -> doc.pixels[y*width+x] != PaintDocument.PAPER })
        for (i in mask.indices) if (mask[i]==0) assertEquals(0,doc.pixels[i])
    }

    @Test fun lightAndHeavySettingsChangeCoverageWithoutLosingAllGrain() {
        val light = paper(); val heavy = paper()
        light.beginStroke(); heavy.beginStroke()
        light.stroke(24f,64f,232f,64f,16f,RED,false,false,.1f)
        heavy.stroke(24f,64f,232f,64f,16f,RED,false,false,.9f)
        val lightPixels = sampleCentre(light); val heavyPixels = sampleCentre(heavy)
        assertTrue(lightPixels.count { it == PaintDocument.PAPER } > heavyPixels.count { it == PaintDocument.PAPER })
        assertTrue(heavyPixels.map(::darkness).average() > lightPixels.map(::darkness).average() + .2)
        assertTrue(heavyPixels.any { darkness(it) < .1 })
    }

    @Test fun diagonalEventSplitsPreserveDistanceSampling() {
        val single = paper(); val split = paper()
        single.beginStroke(); split.beginStroke()
        single.stroke(20f,20f,220f,100f,12f,RED,false,false)
        for (i in 0 until 20) split.stroke(20f+i*10f,20f+i*4f,30f+i*10f,24f+i*4f,12f,RED,false,false)
        assertArrayEquals(single.pixels,split.pixels)
    }

    @Test fun historicalPointsFollowTheCurveAndIncludeTheReleasePoint() {
        val batched = paper(); val individual = paper()
        val historyX = floatArrayOf(50f,90f,140f)
        val historyY = floatArrayOf(35f,90f,30f)
        val batch = PaintGesture(batched,20f,64f,9f,RED,false,false,.5f)
        batch.appendBatch(historyX.size,{ historyX[it] },{ historyY[it] },220f,80f)
        val separate = PaintGesture(individual,20f,64f,9f,RED,false,false,.5f)
        for (i in historyX.indices) separate.append(historyX[i],historyY[i])
        separate.append(220f,80f)
        assertArrayEquals(individual.pixels,batched.pixels)
        assertTrue((86..94).any { y -> batched.pixels[y*256+90] != PaintDocument.PAPER })
        assertTrue((76..84).any { y -> batched.pixels[y*256+218] != PaintDocument.PAPER })
        batched.undo()
        assertTrue(batched.pixels.all { it == PaintDocument.PAPER })
    }

    @Test fun crossedColoursRetainTheUnderlayerBetweenDirectionalWaxDeposits() {
        val doc = paper()
        pass(doc)
        val red = doc.pixels.copyOf()
        doc.beginStroke()
        doc.stroke(128f,15f,128f,113f,16f,BLUE,false,false,.4f)
        val overlap = (55..73).flatMap { y -> (119..137).map { x -> y*256+x } }
        assertTrue(overlap.any { i -> (doc.pixels[i] and 255) > (red[i] and 255) + 30 })
        assertTrue(overlap.any { i -> (doc.pixels[i] ushr 16 and 255) > (doc.pixels[i] and 255) + 30 })
        assertTrue(overlap.map { doc.pixels[it] }.distinct().size > overlap.size / 3)
    }

    @Test fun invalidSamplesDoNotDamagePixelsOrBreakContinuation() {
        val doc = paper(); val expected = paper()
        doc.beginStroke(); expected.beginStroke()
        doc.stroke(24f,64f,100f,64f,16f,RED,false,false)
        doc.stroke(Float.NaN,64f,120f,64f,16f,RED,false,false)
        doc.stroke(100f,64f,232f,64f,16f,RED,false,false)
        expected.stroke(24f,64f,232f,64f,16f,RED,false,false)
        assertArrayEquals(expected.pixels,doc.pixels)
    }

    private fun paper() = PaintDocument(256,128,IntArray(256*128) { 1 })
    private fun pass(doc: PaintDocument) {
        doc.beginStroke()
        doc.stroke(24f,64f,232f,64f,16f,RED,false,false)
    }
    private fun sampleCentre(doc: PaintDocument) = (57..71).flatMap { y -> (40..215).map { x -> doc.pixels[y*doc.width+x] } }
    private fun darkness(color: Int) = 1.0 - ((color ushr 8) and 255).toDouble() / ((PaintDocument.PAPER ushr 8) and 255)
    companion object { const val RED = -65536; const val BLUE = -16776961 }
}
