package com.bugworld.app

import com.bugworld.app.data.Species
import com.bugworld.app.drawing.ArtworkRasterMapper
import com.bugworld.app.drawing.PaintDocument
import org.junit.Assert.*
import org.junit.Test
import java.io.File

class ArtworkRasterMapperTest {
    @Test fun sheetUvUsesTheSamePixelsForEveryNewSpeciesWithoutMirroringOrFlipping() {
        val runtime=File(root,"app/src/main/assets/v3/templates")
        for (species in Species.entries.filter { it.sheetMaterial!=null }) {
            val slug=species.asset
            val mask=PngTestPixels.read(File(runtime,"$slug-mask.png"))
            val ink=PngTestPixels.read(File(runtime,"$slug-lines.png"))
            val regions=IntArray(mask.pixels.size) { mask.pixels[it] ushr 16 and 255 }
            val transfer=ArtworkRasterMapper(species,mask.width,mask.height,regions,ink.pixels)
            val material=requireNotNull(species.sheetMaterial)
            val marks=IntArray(regions.size)
            val known=linkedMapOf<Int,Int>()
            for (i in regions.indices) if (regions[i]>0 && ink.pixels[i] ushr 24==0) {
                known.putIfAbsent(regions[i],i)
            }
            assertEquals(regions.maxOrNull(),known.size)
            for ((id,i) in known) marks[i]=if (id%2==0) RED else BLUE
            val result=transfer.mapPixels(marks,mask.width).getValue(material)
            for (i in known.values) {
                assertEquals(marks[i],result[i])
                val u=(i%mask.width+.5f)/mask.width
                val v=(i/mask.width+.5f)/mask.height
                assertEquals(marks[i],transfer.sample(material,u,v,marks))
            }
        }
    }
    @Test fun neutralReliefModulatesPigmentWithoutChangingItsHueOrThePaperInk() {
        val species=Species.HONEYBEE
        val color=0xFF804020.toInt()
        val mapper=ArtworkRasterMapper(species,2,2, intArrayOf(1,1,1,0),
            intArrayOf(0,0,0xFF221100.toInt(),0),byteArrayOf(96,128.toByte(),148.toByte(),128.toByte()))
        val rgba=mapper.mapPixels(IntArray(4) { color },2).getValue(requireNotNull(species.sheetMaterial))
        assertArrayEquals(intArrayOf(0xFF603018.toInt(),color,0xFF221100.toInt(),PaintDocument.PAPER),rgba)
    }
    private val root = listOf(File("."),File("..")).first { File(it,"assets-src/v3-review/lineart").isDirectory }
    private fun mapper(species: Species, runtime: Boolean=false): ArtworkRasterMapper {
        val asset=species.asset
        val mask = PngTestPixels.read(File(root,if(runtime) "app/src/main/assets/v3/templates/$asset-mask.png"
            else "assets-src/v3-review/lineart/masks/$asset-regions-2048.png"))
        val ink = PngTestPixels.read(File(root,if(runtime) "app/src/main/assets/v3/templates/$asset-lines.png"
            else "assets-src/v3-review/lineart/sheets/$asset-outline-2048.png"))
        return ArtworkRasterMapper(species, mask.width, mask.height,
            mask.pixels.map { it ushr 16 and 255 }.toIntArray(), ink.pixels)
    }

    @Test fun runtimeResolutionAndCachedProjectionKeepNewAsymmetricPaint() {
        val mapper=mapper(Species.BUTTERFLY,runtime=true)
        assertEquals(1024,mapper.width); assertEquals(1024,mapper.height)
        val pixels=IntArray(1024*1024) { PaintDocument.PAPER }
        mark(pixels,276,359,RED,1024); mark(pixels,740,359,BLUE,1024)
        val material="Continuous wax pigment • image PBR"
        val first=mapper.mapPixels(pixels).getValue(material)
        assertEquals(RED,first[353*1024+288]); assertEquals(BLUE,first[353*1024+735])
        mark(pixels,276,359,BLUE,1024)
        val second=mapper.mapPixels(pixels).getValue(material)
        assertEquals(BLUE,second[353*1024+288])
        assertEquals(RED,first[353*1024+288])
    }

    @Test fun butterflyAsymmetricForewingLandmarksKeepTheirSideAndVerticalDirection() {
        val mapper = mapper(Species.BUTTERFLY)
        // Source crop points (120,100) and (382,100); GLB atlas UVs are (.281667,.345) / (.718333,.345).
        // Approved sheet transform puts these at (553,718) and (1481,718), independent of mapper formulas.
        val pixels = IntArray(2048*2048) { PaintDocument.PAPER }
        mark(pixels,553,718,RED); mark(pixels,1481,718,BLUE)
        val material = "Continuous wax pigment • image PBR"
        assertEquals(RED,mapper.sample(material,.28166667f,.345f,pixels))
        assertEquals(BLUE,mapper.sample(material,.71833333f,.345f,pixels))
        assertEquals(PaintDocument.PAPER,mapper.sample(material,.28166667f,.655f,pixels))
    }

    @Test fun ladybugIndependentShellMapsTransferMarksAtTheDorsalHalfOfEachShell() {
        val mapper = mapper(Species.LADYBUG)
        val left = mapper.sourcePoint("left_pink_wax",.5f,2f/3f)
        val right = mapper.sourcePoint("right_mint_wax",.5f,2f/3f)
        // At exported V=2/3 the half-shell arch is 30 degrees: half the distance from seam to edge.
        assertTrue("Left shell must sample the left half",left.x in 630f..710f)
        assertTrue("Right shell must sample the right half",right.x in 1300f..1400f)
        assertTrue(left.y in 1130f..1170f); assertTrue(right.y in 1130f..1170f)
        val pixels = IntArray(2048*2048) { PaintDocument.PAPER }
        for (y in 1120..1180) for (x in 885..910) pixels[y*2048+x] = RED
        for (y in 1120..1180) for (x in 1125..1150) pixels[y*2048+x] = BLUE
        // V=.9 samples clear pigment between the dark spot and the seam at source x≈894 / 1134.
        val seamLeft = mapper.sourcePoint("left_pink_wax",.5f,1f)
        val seamRight = mapper.sourcePoint("right_mint_wax",.5f,1f)
        assertTrue(seamLeft.x > left.x); assertTrue(seamRight.x < right.x)
        assertEquals(RED,mapper.sample("left_pink_wax",.5f,.9f,pixels))
        assertEquals(BLUE,mapper.sample("right_mint_wax",.5f,.9f,pixels))
    }

    @Test fun beetleShellAndBothHornRegionsUseTheAuthoredProfileUv() {
        val mapper = mapper(Species.BEETLE)
        val upper = mapper.sourcePoint("left_green_elytron",.5f,1f)
        val lower = mapper.sourcePoint("left_green_elytron",.5f,0f)
        assertTrue(upper.x in 630f..670f); assertTrue(upper.y in 890f..950f)
        assertTrue(lower.y in 1270f..1320f)
        val horn = mapper.sourcePoint("warm_ivory_wax",.75f,.25f)
        assertTrue("Horn mapping must use full source profile X", horn.x in 1740f..1770f)
        assertTrue("Exported V grows down the approved horn drawing", horn.y in 615f..650f)
        val pronotum = mapper.sourcePoint("lavender_pronotum",.5f,.5f)
        assertTrue(pronotum.x in 1290f..1325f); assertTrue(pronotum.y in 940f..950f)
    }

    @Test fun caterpillarTenIntervalsKeepTailHeadAndDorsalVentralMarksDistinct() {
        val mapper = mapper(Species.CATERPILLAR)
        val material = "Continuous wax pigment • image PBR"
        val tail = mapper.sourcePoint(material,.03f,0f)
        val head = mapper.sourcePoint(material,.95f,0f)
        assertTrue(tail.x in 210f..255f); assertTrue(head.x in 1760f..1820f)
        val top = mapper.sourcePoint(material,.4275f,.25f)
        val bottom = mapper.sourcePoint(material,.4275f,.75f)
        assertTrue(top.x in 925f..960f); assertTrue(top.y in 890f..950f)
        assertTrue(bottom.y in 1190f..1230f)
        val pixels = IntArray(2048*2048) { PaintDocument.PAPER }
        // Interior marks avoid the intentionally protected silhouette line.
        for (y in 940..1040) for (x in 925..970) pixels[y*2048+x] = RED
        for (y in 1110..1170) for (x in 925..970) pixels[y*2048+x] = BLUE
        assertEquals(RED,mapper.sample(material,.4275f,.08f,pixels))
        assertEquals(BLUE,mapper.sample(material,.4275f,.58f,pixels))
    }

    @Test fun fixedButterflyTipInkCannotBePaintedOver() {
        val mapper = mapper(Species.BUTTERFLY)
        val pixels = IntArray(2048*2048) { RED }
        val color = mapper.sample("Continuous wax pigment • image PBR",.13333334f,.21f,pixels)
        assertTrue("Protected tip remains dark", (color ushr 16 and 255) < 120)
        assertTrue((color ushr 8 and 255) < 100)
    }

    @Test fun caterpillarWrapTransfersPigmentWithoutTurningPaperOutlineIntoADorsalStripe() {
        val transfer = mapper(Species.CATERPILLAR, runtime=true)
        val mask = PngTestPixels.read(File(root,"app/src/main/assets/v3/templates/caterpillar-mask.png"))
        val colors = intArrayOf(0,0xFFBA91DF.toInt(),0xFFEE95B9.toInt(),0xFF84B5EB.toInt(),
            0xFFE3B0CE.toInt(),0xFF77B2E0.toInt(),0xFFA8C97D.toInt(),0xFFEF9791.toInt(),
            0xFFB28BDD.toInt(),0xFF86C8BF.toInt(),0xFFF1B65D.toInt())
        val pigment = IntArray(mask.pixels.size) { colors[mask.pixels[it] ushr 16 and 255] }
        val material = "Continuous wax pigment • image PBR"
        val mapped = transfer.mapPixels(pigment).getValue(material)
        // Optional actual Kotlin atlas for importing into the shipped GLB in Blender.
        System.getenv("BUGWORLD_TEXTURE_PROOF_DIR")?.let { directory ->
            File(directory).mkdirs()
            java.io.DataOutputStream(File(directory,"caterpillar.argb").outputStream().buffered()).use { out ->
                out.writeInt(1024); out.writeInt(512); mapped.forEach(out::writeInt)
            }
        }
        val centers = floatArrayOf(.03f,.1125f,.2175f,.3225f,.4275f,.5325f,.6375f,.7425f,.8475f,.95f)
        for ((segment,u) in centers.withIndex()) for (v in floatArrayOf(0f,.20f,.25f,.30f,.5f,.75f)) {
            assertEquals("Segment ${segment+1} at V=$v retains painted color",colors[segment+1],
                transfer.sample(material,u,v,pigment))
            val x=(u*1024).toInt(); val y=(v*512).toInt()
            assertEquals(colors[segment+1],mapped[y*1024+x])
        }
        // Do not remove dark colors chosen by the player along with the template outline.
        val dark = 0xFF27202B.toInt()
        val darkPigment = IntArray(pigment.size) { if (pigment[it]==0) 0 else dark }
        assertEquals(dark,transfer.sample(material,.4275f,.25f,darkPigment))
    }

    private fun mark(pixels: IntArray, x: Int, y: Int, color: Int, width: Int=2048) {
        for (iy in y-5..y+5) for (ix in x-5..x+5) pixels[iy*width+ix] = color
    }
    companion object { private const val RED = -65536; private const val BLUE = -16776961 }
}
