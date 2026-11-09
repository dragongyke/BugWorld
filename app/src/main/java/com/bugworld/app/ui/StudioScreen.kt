package com.bugworld.app.ui

import android.graphics.BitmapFactory
import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.*
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.bugworld.app.*
import com.bugworld.app.R
import com.bugworld.app.data.Species
import com.pico.spatial.ui.design.Text
import com.pico.spatial.ui.foundation.window.Augment
import com.pico.spatial.ui.foundation.window.AugmentContentAlignment
import com.pico.spatial.ui.foundation.geometry.DpOffset3D
import com.pico.spatial.ui.foundation.geometry.NormalizedPoint3D

val Night = Color(0xFFF8F4F3)
val Panel = Color(0xFFFFFDF8)
val Lavender = Color(0xFFE8DAF9)
val Muted = Color(0xFF93849D)
val Ink = Color(0xFF55416E)
val Accent = Color(0xFF9778BE)
private val Border = Color(0xFFE8DEED)

@Composable fun Action(label: String, active: Boolean=false, enabled: Boolean=true, modifier: Modifier=Modifier, icon: String?=null, click: ()->Unit) {
    val foreground=if(!enabled) Muted.copy(alpha=.5f) else if(active) Color.White else Ink
    HoverSurface(modifier.heightIn(min=52.dp).semantics { role=Role.Button; contentDescription=label },
        enabled=enabled,shape=RoundedCornerShape(20.dp),background=if(active) Accent else Panel,
        border=if(active) Accent else Border,highlight=if(active) Ink.copy(alpha=.3f) else Lavender.copy(alpha=.65f),click=click) {
        Row(Modifier.padding(horizontal=16.dp,vertical=12.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            if(icon!=null) LineIcon(icon,Modifier.size(24.dp),foreground)
            Text(label,color=foreground,fontSize=18.sp)
        }
    }
}
@Composable fun WindowSurface(modifier: Modifier=Modifier, content: @Composable BoxScope.()->Unit) {
    Box(modifier.fillMaxSize().clip(RoundedCornerShape(28.dp)).background(Night.copy(alpha=.96f))
        .border(2.dp,Color.White.copy(alpha=.9f),RoundedCornerShape(28.dp)).padding(24.dp),content=content)
}

/** The paper is the only editor. Album selection never replaces it implicitly. */
@Composable fun CanvasScreen(state: BugWorldState, previewVisible: Boolean, hidePreview: ()->Unit, preview: ()->Unit, enterGarden: ()->Unit, tools: ()->Unit,
    close: ()->Unit) {
    var confirmNew by remember { mutableStateOf(false) }
    var soundSettings by remember { mutableStateOf(false) }
    val revision=state.revision
    WindowSurface {
        Column(Modifier.fillMaxSize(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(16.dp)) {
                Text(stringResource(state.species.labelRes),color=Ink,fontSize=24.sp,fontWeight=FontWeight.Bold)
                Text(if(state.busy) stringResource(R.string.please_wait) else state.message.localized(),color=Muted,fontSize=15.sp,modifier=Modifier.weight(1f),maxLines=2)
                Action(stringResource(R.string.new_paper),enabled=state.ready && !state.busy) { confirmNew=true }
                IconButton(stringResource(R.string.tools),"crayon",click=tools)
                IconButton(stringResource(R.string.close_canvas),"close",click=close)
            }
            Box(Modifier.weight(1f).fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(Panel).border(1.dp,Color.White,RoundedCornerShape(18.dp))) {
                AndroidView(factory={ PaintView(it,state) },modifier=Modifier.fillMaxSize(),update={ revision; it.state=state; it.refresh() })
            }
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(8.dp),verticalAlignment=Alignment.CenterVertically) {
                Action(stringResource(R.string.sound)) { soundSettings=!soundSettings }
                Action(stringResource(R.string.go_garden),enabled=state.ready && !state.busy,icon="leaf",click=enterGarden)
                Spacer(Modifier.weight(1f))
                Action(stringResource(R.string.save),enabled=state.ready && !state.busy,icon="save") { state.save() }
                if(state.editedId!=null) IconButton(stringResource(R.string.save_copy),"save",enabled=!state.busy) { state.save(true) }
                Action(stringResource(if(previewVisible) R.string.hide_preview else R.string.show_preview),enabled=state.ready && !state.busy,icon="preview") {
                    if(previewVisible) hidePreview() else state.preview(done=preview)
                }
                Action(stringResource(R.string.release),true,state.ready && !state.busy && state.pendingRelease==null,icon="leaf") { state.save { state.place(it,enterGarden) } }
            }
        }
        if(soundSettings) Box(Modifier.fillMaxSize().background(Ink.copy(alpha=.25f)),contentAlignment=Alignment.Center) {
            Column(Modifier.width(360.dp).background(Panel,RoundedCornerShape(24.dp)).padding(24.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
                Text(stringResource(R.string.garden_sound),color=Ink,fontSize=24.sp)
                Action(stringResource(R.string.music_percent,(state.musicVolume*100).toInt())) { state.musicVolume=nextGardenVolume(state.musicVolume) }
                Action(stringResource(R.string.nature_percent,(state.natureVolume*100).toInt())) { state.natureVolume=nextGardenVolume(state.natureVolume) }
                Action(stringResource(R.string.done)) { soundSettings=false }
            }
        }
        if(confirmNew) Confirmation(stringResource(R.string.new_confirm_title),stringResource(R.string.new_confirm_message),{ confirmNew=false }) { state.newCanvas(); confirmNew=false }
    }
}
@Composable fun SpeciesBar(state: BugWorldState, albumOpen: Boolean, openCanvas: ()->Unit, album: ()->Unit) {
    val species=Species.entries
    val itemWidth=68.dp
    val gap=8.dp
    val stripWidth=if(species.size>=5) itemWidth*4.5f + gap*4 else itemWidth*species.size + gap*(species.size-1)
    val logoLabel=stringResource(R.string.brand_canvas)
    val albumLabel=stringResource(R.string.album)
    val enabled=state.ready && !state.busy
    // Same top anchor and offset as SDK 6.1.0 TabBar. The Augment itself has no click handler.
    Augment(anchor=NormalizedPoint3D.TopFront,alignment=AugmentContentAlignment.TopCenter,
        offset=DpOffset3D(0.dp,(-88).dp,0.dp),enableMaterialBackground=false) {
        val scroll=rememberLazyListState()
        LaunchedEffect(state.species) {
            val index=species.indexOf(state.species)
            val layout=scroll.layoutInfo
            val visible=layout.visibleItemsInfo.any { it.index==index && it.offset>=layout.viewportStartOffset &&
                it.offset+it.size<=layout.viewportEndOffset }
            if (!visible && index!=scroll.firstVisibleItemIndex) scroll.scrollToItem(index)
        }
        Row(Modifier.background(Panel,RoundedCornerShape(26.dp)).border(1.dp,Border,RoundedCornerShape(26.dp)).padding(8.dp),
            verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(gap)) {
            HoverSurface(Modifier.size(120.dp,52.dp).semantics { contentDescription=logoLabel; role=Role.Button },click=openCanvas) {
                AssetImage("brand/bugworld-logo.png",null,Modifier.size(96.dp,24.dp))
            }
            LazyRow(Modifier.width(stripWidth),state=scroll,horizontalArrangement=Arrangement.spacedBy(gap)) {
                items(species,key={it.asset}) { insect ->
                    val name=stringResource(insect.labelRes)
                    val isSelected=state.species==insect
                    HoverSurface(Modifier.size(itemWidth,52.dp).semantics { contentDescription=name; role=Role.Tab; selected=isSelected },
                        enabled=enabled,background=if(isSelected) Lavender else Panel,border=if(isSelected) Accent else Border,
                        click={ state.selectSpecies(insect); openCanvas() }) {
                        SpeciesIcon(insect,Modifier.size(40.dp))
                    }
                }
            }
            HoverSurface(Modifier.height(52.dp).semantics { contentDescription=albumLabel; role=Role.Button; selected=albumOpen },
                background=if(albumOpen) Lavender else Panel,click=album) {
                Row(Modifier.padding(horizontal=16.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                    LineIcon("album",Modifier.size(24.dp)); Text(albumLabel,color=Ink,fontSize=16.sp)
                }
            }
        }
    }
}
@Composable fun SpeciesIcon(species: Species, modifier: Modifier) {
    AssetImage("species/${species.asset}-96.png",null,modifier)
}
@Composable fun ToolScreen(state: BugWorldState, close: ()->Unit) {
    val canUndo=remember(state.document,state.revision) { state.document.canUndo }
    val canRedo=remember(state.document,state.revision) { state.document.canRedo }
    val panelLabel=stringResource(R.string.tools_panel)
    val mirrorLabel=stringResource(R.string.mirror)
    WindowSurface(Modifier.semantics { contentDescription=panelLabel }) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                Text(stringResource(R.string.tools),color=Ink,fontSize=26.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f))
                IconButton(stringResource(R.string.close_tools),"close",click=close)
            }
            Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                listOf(Triple(PaintTool.CRAYON,R.string.crayon,"crayon"),Triple(PaintTool.FILL,R.string.fill,"fill"),Triple(PaintTool.ERASER,R.string.eraser,"eraser")).forEach { (tool,labelRes,icon) ->
                    val label=stringResource(labelRes)
                    HoverSurface(Modifier.weight(1f).semantics { contentDescription=label; role=Role.Button; selected=state.tool==tool },background=if(state.tool==tool) Lavender else Panel,border=Border,click={ state.tool=tool }) {
                    Column(Modifier.padding(vertical=14.dp),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(9.dp)) {
                        LineIcon(icon,Modifier.size(30.dp)); Text(label,color=Ink,fontSize=17.sp)
                    }
                    }
                }
            }
            Column(verticalArrangement=Arrangement.spacedBy(10.dp)) {
                Palette.chunked(5).forEach { colors ->
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                        colors.forEachIndexed { index,swatch ->
                            val (argb,labelRes)=swatch
                            val name=stringResource(labelRes)
                            val isSelected=state.color==argb
                            HoverSurface(Modifier.size(54.dp).semantics { contentDescription=name; role=Role.Button; selected=isSelected },
                                enabled=state.tool!=PaintTool.ERASER && !state.busy,shape=RoundedCornerShape(50),background=Color(argb),borderWidth=if(isSelected) 3.dp else 1.dp,
                                border=if(isSelected) Ink else Border,highlight=Color.White.copy(alpha=.25f),click={state.color=argb}) {
                                Canvas(Modifier.fillMaxSize()) { repeat(12) { i ->
                                    val x=(i*17+index*11)%54/54f*size.width
                                    drawLine(Color.White.copy(alpha=.17f),Offset(x,0f),Offset(x-size.width*.45f,size.height),1.dp.toPx())
                                } }
                                if(isSelected) Canvas(Modifier.size(20.dp)) {
                                    drawCircle(Ink)
                                    val joint=Offset(size.width*.43f,size.height*.68f)
                                    drawLine(Color.White,Offset(size.width*.23f,size.height*.49f),joint,2.dp.toPx())
                                    drawLine(Color.White,joint,Offset(size.width*.77f,size.height*.31f),2.dp.toPx())
                                }
                            }
                        }
                    }
                }
            }
            ValueSlider(stringResource(R.string.width),(state.radius-4f)/20f) { state.radius=4f+it*20f }
            ValueSlider(stringResource(R.string.strength),state.brushStrength) { state.brushStrength=it.coerceIn(.08f,1f) }
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceBetween) {
                Text(mirrorLabel,color=if(state.species==Species.BUTTERFLY) Ink else Muted,fontSize=18.sp)
                HoverSurface(Modifier.size(66.dp,48.dp).semantics { contentDescription=mirrorLabel; role=Role.Switch; toggleableState=if(state.mirror) androidx.compose.ui.state.ToggleableState.On else androidx.compose.ui.state.ToggleableState.Off },
                    enabled=state.species==Species.BUTTERFLY,shape=RoundedCornerShape(50),background=if(state.mirror) Accent else Border,click={state.mirror=!state.mirror}) {
                    Box(Modifier.align(if(state.mirror) Alignment.CenterEnd else Alignment.CenterStart).padding(4.dp).size(30.dp).background(Color.White,CircleShape))
                }
            }
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                IconButton(stringResource(R.string.undo),"undo",Modifier.weight(1f),canUndo && !state.busy) { state.undo() }
                IconButton(stringResource(R.string.redo),"redo",Modifier.weight(1f),canRedo && !state.busy) { state.redo() }
            }
        }
    }
}
@Composable private fun ValueSlider(label: String, value: Float, changed: (Float)->Unit) {
    val update by rememberUpdatedState(changed)
    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(20.dp)) {
        Text(label,color=Ink,fontSize=18.sp,modifier=Modifier.widthIn(min=68.dp))
        Canvas(Modifier.weight(1f).height(48.dp).semantics { contentDescription=label; progressBarRangeInfo=ProgressBarRangeInfo(value,0f..1f); setProgress { update(it.coerceIn(0f,1f)); true } }
            .pointerInput(Unit) { detectTapGestures { update((it.x/size.width).coerceIn(0f,1f)) } }
            .pointerInput(Unit) { detectDragGestures(onDragStart={ update((it.x/size.width).coerceIn(0f,1f)) }) { event,_ -> event.consume(); update((event.position.x/size.width).coerceIn(0f,1f)) } }) {
            val inset=11.dp.toPx(); val x=inset+(size.width-2*inset)*value.coerceIn(0f,1f)
            drawLine(Border,Offset(inset,center.y),Offset(size.width-inset,center.y),6.dp.toPx(),androidx.compose.ui.graphics.StrokeCap.Round)
            drawLine(Accent,Offset(inset,center.y),Offset(x,center.y),6.dp.toPx(),androidx.compose.ui.graphics.StrokeCap.Round)
            drawCircle(Muted.copy(alpha=.15f),12.dp.toPx(),Offset(x,center.y+2.dp.toPx())); drawCircle(Color.White,11.dp.toPx(),Offset(x,center.y))
            drawCircle(Border,11.dp.toPx(),Offset(x,center.y),style=Stroke(1.dp.toPx()))
        }
    }
}
@Composable fun IconButton(label: String, icon: String, modifier: Modifier=Modifier, enabled: Boolean=true, click: ()->Unit) {
    HoverSurface(modifier.sizeIn(minWidth=48.dp,minHeight=48.dp).semantics { contentDescription=label; role=Role.Button },
        enabled=enabled,shape=RoundedCornerShape(14.dp),background=Color.Transparent,click=click) {
        Box(Modifier.padding(11.dp)) { LineIcon(icon,Modifier.size(26.dp),if(enabled) Ink else Muted.copy(alpha=.4f)) }
    }
}
@Composable fun LineIcon(name: String, modifier: Modifier=Modifier, color: Color=Ink) {
    AssetImage("icons/$name-64.png",null,modifier,ColorFilter.tint(color))
}
@Composable private fun AssetImage(path: String, description: String?, modifier: Modifier, tint: ColorFilter?=null) {
    val context=LocalContext.current
    val bitmap=remember(context,path) {
        context.assets.open("v3/ui/$path").use { stream ->
            requireNotNull(BitmapFactory.decodeStream(stream)) { "Invalid approved UI image: $path" }.asImageBitmap()
        }
    }
    Image(bitmap,description,modifier,colorFilter=tint)
}
@Composable fun Confirmation(title: String, message: String, cancel: ()->Unit, confirm: ()->Unit) {
    Box(Modifier.fillMaxSize().background(Ink.copy(alpha=.32f)).clickable(onClick=cancel),contentAlignment=Alignment.Center) {
        Column(Modifier.widthIn(max=460.dp).padding(12.dp).clip(RoundedCornerShape(24.dp)).background(Panel).clickable {}.padding(24.dp),verticalArrangement=Arrangement.spacedBy(20.dp)) {
            Text(title,color=Ink,fontSize=24.sp,fontWeight=FontWeight.Bold); Text(message,color=Muted,fontSize=18.sp)
            Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) { Action(stringResource(R.string.cancel),click=cancel); Action(stringResource(R.string.confirm),true,click=confirm) }
        }
    }
}
private val Palette=listOf(
    0xFFE985B6.toInt() to R.string.swatch_sakura,
    0xFFBC8BE0.toInt() to R.string.swatch_lilac,
    0xFF986BD3.toInt() to R.string.swatch_iris,
    0xFF7E9EDF.toInt() to R.string.swatch_sky,
    0xFF78C6AC.toInt() to R.string.swatch_mint,
    0xFF50B3BA.toInt() to R.string.swatch_lake,
    0xFFE7B65E.toInt() to R.string.swatch_honey,
    0xFFEB937D.toInt() to R.string.swatch_coral,
    0xFFD6A6B6.toInt() to R.string.swatch_dusty_rose,
    0xFFC5B49E.toInt() to R.string.swatch_oat,
    0xFFA6A5B1.toInt() to R.string.swatch_mist,
    0xFF777484.toInt() to R.string.swatch_slate,
    0xFFDC555B.toInt() to R.string.swatch_poppy,
    0xFFF2A34F.toInt() to R.string.swatch_apricot,
    0xFFF6DA64.toInt() to R.string.swatch_lemon,
    0xFF8EBD65.toInt() to R.string.swatch_leaf,
    0xFF388467.toInt() to R.string.swatch_forest,
    0xFF4389C9.toInt() to R.string.swatch_ocean,
    0xFF40536C.toInt() to R.string.swatch_navy,
    0xFFFFF5D9.toInt() to R.string.swatch_ivory
)

private fun nextGardenVolume(value: Float)=when { value<.24f -> .25f; value<.49f -> .5f; value<.74f -> .75f; else -> 0f }
