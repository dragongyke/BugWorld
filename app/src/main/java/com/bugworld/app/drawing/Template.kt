package com.bugworld.app.drawing

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import com.bugworld.app.data.Species

class Template(context: Context, val species: Species, val version: Int = CURRENT_VERSION) {
    init { require(version == CURRENT_VERSION) { "Only approved v3 templates can be opened; migrate saved pixels with documentFrom." } }
    private val folder = "v3/templates"
    val outline: Bitmap by lazy { context.assets.open("$folder/${species.asset}-lines.png").use {
        requireNotNull(BitmapFactory.decodeStream(it)) { "Invalid ${species.asset} outline" }
    } }
    val surface: Bitmap get() = outline
    val width get() = outline.width
    val height get() = outline.height
    val regions: IntArray by lazy { context.assets.open("$folder/${species.asset}-mask.png").use { input ->
        val mask = requireNotNull(BitmapFactory.decodeStream(input)) { "Invalid ${species.asset} region mask" }
        try {
            require(mask.width==width && mask.height==height)
            IntArray(width*height).also { pixels ->
                mask.getPixels(pixels,0,width,0,0,width,height)
                for (i in pixels.indices) pixels[i] = pixels[i] ushr 16 and 255
            }
        } finally { mask.recycle() }
    } }
    internal val rasterMapper by lazy {
        val ink = IntArray(width*height).also { outline.getPixels(it,0,width,0,0,width,height) }
        val detail=species.sheetMaterial?.let {
            context.assets.open("$folder/${species.asset}-detail.png").use { stream ->
                val bitmap=requireNotNull(BitmapFactory.decodeStream(stream))
                try {
                    require(bitmap.width==width && bitmap.height==height)
                    val pixels=IntArray(width*height)
                    bitmap.getPixels(pixels,0,width,0,0,width,height)
                    ByteArray(pixels.size) { i -> (pixels[i] ushr 16).toByte() }
                } finally { bitmap.recycle() }
            }
        }
        ArtworkRasterMapper(species,width,height,regions,ink,detail)
    }

    fun newDocument() = PaintDocument(width,height,regions,
        if (species == Species.BUTTERFLY) (64f+251f*1.77075099f)*width/1024f-.5f else (width-1)/2f)

    /** Always returns v3 dimensions and mask. Caller must keep old PNG bytes before persisting a migrated work. */
    fun documentFrom(bitmap: Bitmap, sourceVersion: Int): PaintDocument {
        val input=IntArray(bitmap.width*bitmap.height).also { bitmap.getPixels(it,0,bitmap.width,0,0,bitmap.width,bitmap.height) }
        val pixels = if (sourceVersion==CURRENT_VERSION && bitmap.width==width && bitmap.height==height) {
            IntArray(width*height) { i -> if (regions[i]==0) 0 else if(input[i] ushr 24==0) PaintDocument.PAPER else input[i] }
        } else ArtworkMigration.migrate(bitmap.width,bitmap.height,input,width,height,regions,
            horizontalBody=species==Species.BEETLE || species==Species.CATERPILLAR,
            rotateClockwise=sourceVersion==1 && species==Species.BEETLE)
        return newDocument().apply { restore(pixels) }
    }

    fun bitmap(document: PaintDocument, withOutline: Boolean = false): Bitmap {
        require(document.width==width && document.height==height)
        val image = Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888)
        image.setPixels(document.pixels,0,width,0,0,width,height)
        if (withOutline) Canvas(image).drawBitmap(outline, 0f, 0f, null)
        return image
    }
    companion object { const val CURRENT_VERSION=3 }
}
