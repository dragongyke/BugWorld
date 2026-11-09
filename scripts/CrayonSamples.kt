import com.bugworld.app.drawing.PaintDocument
import com.bugworld.app.drawing.PaintGesture
import java.awt.Color
import java.awt.Font
import java.awt.RenderingHints
import java.awt.image.BufferedImage
import java.io.File
import javax.imageio.ImageIO
import kotlin.math.*

// This is the app's PaintDocument renderer on the JVM, with AWT used only to assemble the sheet.
private const val PINK = 0xFFE64F85.toInt()
private const val VIOLET = 0xFF9565BC.toInt()
private const val BLUE = 0xFF657CCB.toInt()
private fun paper() = PaintDocument(1024,1024,IntArray(1024*1024) { 1 })

private fun hatch(doc: PaintDocument, passes: Int, strength: Float, color: Int, reverse: Boolean = false) {
    repeat(passes) { layer ->
        val offset = layer * 1.7f
        for (line in 0..22) {
            val x = 38f + line*15f + offset
            val y = 205f + 12f*sin(line*.66f)
            val endX = x + 66f
            val endY = y - 105f + 10f*sin(line*.91f)
            val startY = if(reverse) 290f-y else y
            val finishY = if(reverse) 290f-endY else endY
            val gesture = PaintGesture(doc,x,startY,10.5f,color,false,false,strength)
            for (i in 1..30) {
                val t = i/30f
                gesture.append(x+(endX-x)*t+1.7f*sin(t*7f+line),startY+(finishY-startY)*t)
            }
        }
    }
}

private fun image(doc: PaintDocument): BufferedImage = BufferedImage(doc.width,doc.height,BufferedImage.TYPE_INT_ARGB).also {
    it.setRGB(0,0,doc.width,doc.height,doc.pixels,0,doc.width)
}

fun main(args: Array<String>) {
    val output = File(args.firstOrNull() ?: "crayon-runtime-v2.png")
    val project = output.absoluteFile.parentFile.parentFile.parentFile.parentFile
    val sheet = BufferedImage(1500,1120,BufferedImage.TYPE_INT_RGB)
    val g = sheet.createGraphics()
    g.setRenderingHint(RenderingHints.KEY_ANTIALIASING,RenderingHints.VALUE_ANTIALIAS_ON)
    g.color = Color(PaintDocument.PAPER); g.fillRect(0,0,sheet.width,sheet.height)
    g.color = Color(0x3B3040); g.font = Font("Microsoft YaHei",Font.BOLD,34)
    g.drawString("BugWorld · 实际蜡笔渲染样张",430,62)
    g.font = Font("Microsoft YaHei",Font.PLAIN,16)
    g.drawString("由应用 PaintDocument.kt 直接输出 · 1024 画纸原像素裁切 · 非概念图 / 非头显截图",370,97)
    val names = arrayOf("轻涂","叠涂","厚涂","交叉叠色","连续曲线","纸纹细节 × 3")
    val notes = arrayOf("轻重 10% · 一次经过","轻重 40% · 两次经过","轻重 80% · 五次经过", "玫红与蓝色 · 保留方向和底层", "历史触点连续输入 · 笔头 9 px", "轻涂与叠色局部 · 最近邻放大")
    val docs = mutableListOf<PaintDocument>()
    repeat(3) { index ->
        val doc = paper()
        hatch(doc,intArrayOf(1,2,5)[index],floatArrayOf(.1f,.4f,.8f)[index],PINK)
        docs += doc
    }
    val crossed = paper()
    hatch(crossed,1,.45f,PINK)
    hatch(crossed,1,.48f,BLUE,true)
    docs += crossed
    val curve = paper()
    val gesture = PaintGesture(curve,34f,150f,9f,VIOLET,false,false,.46f)
    for (i in 1..700) {
        val t = i/700f
        gesture.append(34f+390f*t,150f+68f*sin(t*5f*PI.toFloat())*(.35f+t*.65f))
    }
    docs += curve
    for (i in 0..5) {
        val x = 30 + i%3*490
        val y = if (i<3) 144 else 572
        g.color = Color(0x3B3040); g.font = Font("Microsoft YaHei",Font.BOLD,27)
        g.drawString(names[i],x+12,y)
        g.font = Font("Microsoft YaHei",Font.PLAIN,16); g.color = Color(0x796977)
        g.drawString(notes[i],x+12,y+30)
        if(i<5) g.drawImage(image(docs[i]),x,y+52,x+460,y+362,0,0,460,310,null)
        else {
            g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR)
            g.drawImage(image(docs[0]),x+5,y+58,x+224,y+355,130,85,203,184,null)
            g.drawImage(image(docs[3]),x+235,y+58,x+454,y+355,130,85,203,184,null)
        }
        g.color = Color(0xD9CEC9); g.drawLine(x,y+389,x+460,y+389)
    }
    g.color = Color(0x796977); g.font = Font("Microsoft YaHei",Font.PLAIN,16)
    g.drawString("固定纸纹、按距离采样、方向性蜡痕、叠色积累；纸纹与颜色直接保存为作品像素。",395,1045)
    g.drawString("生成命令：scripts/verify_crayon.ps1 -Render",520,1077)
    g.dispose()
    output.parentFile.mkdirs()
    ImageIO.write(sheet,"png",output)
    for ((i,doc) in docs.withIndex()) {
        val values = (95..195).flatMap { y -> (160..320).map { x -> doc.pixels[y*doc.width+x] } }
        println("Sample ${i+1}: paper=${"%.2f".format(100.0*values.count { it==PaintDocument.PAPER }/values.size)}%, distinct=${values.distinct().size}")
    }
    // Separate clipping example reads the same region mask and outline as the app when available.
    val v2 = File(project,"app/src/main/assets/v2/templates/butterfly-mask.png")
    val maskFile = if(v2.exists()) v2 else File(project,"app/src/main/assets/templates/butterfly-mask.png")
    if(maskFile.exists()) {
        val mask = ImageIO.read(maskFile)
        val pixels = mask.getRGB(0,0,mask.width,mask.height,null,0,mask.width)
        val doc = PaintDocument(mask.width,mask.height,IntArray(pixels.size) { pixels[it] ushr 16 and 255 })
        val scale = mask.width/512f
        for (line in 0..45) {
            doc.beginStroke()
            doc.stroke(30f*scale,line*12f*scale,240f*scale,(line*12f-70)*scale,14f*scale,
                if(line<25) PINK else VIOLET,true,false,.42f)
        }
        val butterfly = image(doc)
        val outlineFile = File(maskFile.parentFile,"butterfly-lines.png")
        if(outlineFile.exists()) butterfly.createGraphics().also { it.drawImage(ImageIO.read(outlineFile),0,0,null); it.dispose() }
        ImageIO.write(butterfly,"png",File(output.parentFile,"crayon-runtime-butterfly-v2.png"))
        println("Butterfly mask: ${maskFile.relativeTo(project)} (${mask.width} x ${mask.height})")
    }
    val benchmark = paper()
    repeat(3) {
        val start = System.nanoTime()
        benchmark.beginStroke()
        for (i in 0 until 100) benchmark.stroke(100f+i*6f,512f,106f+i*6f,512f,26f,VIOLET,false,false)
        println("1024 CPU sample ${it+1}: 600 px stroke / 26 px radius = ${(System.nanoTime()-start)/1_000_000} ms (desktop JVM; not headset timing)")
    }
    println(output.absolutePath)
}
