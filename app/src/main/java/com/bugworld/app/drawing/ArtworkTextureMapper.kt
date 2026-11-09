package com.bugworld.app.drawing

import android.content.Context
import android.graphics.Bitmap
import com.bugworld.app.data.Species

/** Converts raw v3 drawing pixels into per-material base-color textures; original PBR maps stay on the material. */
class ArtworkTextureMapper(private val templates: Map<Species,Template>) {
    constructor(context: Context) : this(Species.entries.associateWith { Template(context,it) })

    /**
     * Input is borrowed and has no composited outline. Output bitmaps belong to the caller.
     * Keys are exact GLB material names; apply only to ArtworkRasterMapper.materialMeshes(species).
     * Row zero is exported glTF V=0: no additional vertical flip is needed.
     * Run on a worker: projection tables are built once, then reused for subsequent strokes.
     */
    fun map(species: Species, bitmap: Bitmap): Map<String,Bitmap> {
        val template=templates.getValue(species)
        require(bitmap.width==template.width && bitmap.height==template.height) { "Migrate artwork to the v3 template before mapping" }
        val pixels=IntArray(bitmap.width*bitmap.height).also { bitmap.getPixels(it,0,bitmap.width,0,0,bitmap.width,bitmap.height) }
        val size=1024
        val height=if (species==Species.CATERPILLAR) size/2 else size
        return template.rasterMapper.mapPixels(pixels,size).mapValues { (_,colors) ->
            Bitmap.createBitmap(colors,size,height,Bitmap.Config.ARGB_8888)
        }
    }
}
