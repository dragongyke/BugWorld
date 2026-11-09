package com.bugworld.app

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.File
import java.util.zip.InflaterInputStream
import kotlin.math.abs

/** Reads our 8-bit RGB/RGBA PNG fixtures without java.desktop (absent from Android's test compiler). */
internal data class PngTestPixels(val width: Int,val height: Int,val pixels: IntArray) {
    companion object {
        fun read(file: File): PngTestPixels {
            var width=0; var height=0; var channels=0
            val compressed=ByteArrayOutputStream()
            DataInputStream(file.inputStream()).use { input ->
                require(input.readLong()==-8552249625308161526L) { "Invalid PNG signature" }
                while (true) {
                    val length=input.readInt()
                    val name=ByteArray(4).also(input::readFully).toString(Charsets.US_ASCII)
                    val data=ByteArray(length).also(input::readFully)
                    input.readInt() // CRC checked by source asset validation; fixtures are repository-local.
                    if (name=="IHDR") DataInputStream(ByteArrayInputStream(data)).use { header ->
                        width=header.readInt(); height=header.readInt()
                        require(header.readUnsignedByte()==8)
                        channels=when(header.readUnsignedByte()) { 2->3; 6->4; else->error("Expected RGB/RGBA fixture") }
                        require(header.readUnsignedByte()==0 && header.readUnsignedByte()==0 && header.readUnsignedByte()==0)
                    }
                    if(name=="IDAT") compressed.write(data)
                    if(name=="IEND") break
                }
            }
            require(width>0 && height>0 && channels>0)
            val bytes=InflaterInputStream(ByteArrayInputStream(compressed.toByteArray())).use { it.readBytes() }
            val stride=width*channels
            require(bytes.size==(stride+1)*height)
            val pixels=IntArray(width*height); var previous=IntArray(stride); var row=IntArray(stride); var at=0
            for (y in 0 until height) {
                val filter=bytes[at++].toInt() and 255
                for (x in 0 until stride) {
                    val a=if(x>=channels) row[x-channels] else 0
                    val b=previous[x]; val c=if(x>=channels) previous[x-channels] else 0
                    val predictor=when(filter) {
                        0->0; 1->a; 2->b; 3->(a+b)/2
                        4->{ val p=a+b-c; val pa=abs(p-a); val pb=abs(p-b); val pc=abs(p-c)
                            if(pa<=pb && pa<=pc) a else if(pb<=pc) b else c }
                        else->error("Invalid PNG filter")
                    }
                    row[x]=((bytes[at++].toInt() and 255)+predictor) and 255
                }
                for(x in 0 until width) {
                    val p=x*channels; val alpha=if(channels==4) row[p+3] else 255
                    pixels[y*width+x]=(alpha shl 24) or (row[p] shl 16) or (row[p+1] shl 8) or row[p+2]
                }
                val swap=previous; previous=row; row=swap
            }
            return PngTestPixels(width,height,pixels)
        }
    }
}
