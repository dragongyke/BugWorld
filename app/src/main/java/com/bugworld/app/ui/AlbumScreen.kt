package com.bugworld.app.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.platform.LocalConfiguration
import com.bugworld.app.R
import com.bugworld.app.labelRes
import com.bugworld.app.localized
import com.bugworld.app.BugWorldState
import com.bugworld.app.data.Artwork
import com.pico.spatial.ui.design.Text
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.text.DateFormat
import java.util.Date

/** selectedId is session-owned: closing the window or entering Stage keeps browsing position. */
@Composable fun AlbumScreen(state: BugWorldState, selectedId: String?, select: (String?)->Unit,
    preview: ()->Unit, enterGarden: ()->Unit, editDone: ()->Unit, newPaper: ()->Unit, close: ()->Unit) {
    var deleting by remember { mutableStateOf<Artwork?>(null) }
    val selected=state.works.firstOrNull { it.id==selectedId } ?: state.works.firstOrNull()
    WindowSurface {
        Column(Modifier.fillMaxSize(),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                Text(stringResource(R.string.album),color=Ink,fontSize=26.sp,fontWeight=FontWeight.Bold,modifier=Modifier.weight(1f))
                IconButton(stringResource(R.string.close_album),"close",click=close)
            }
            Text(stringResource(R.string.album_intro),color=Muted,fontSize=16.sp)
            if(state.works.isEmpty()) {
                Column(Modifier.fillMaxWidth().weight(1f),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center) {
                    LineIcon("album",Modifier.size(56.dp),Accent)
                    Spacer(Modifier.height(24.dp))
                    Text(stringResource(R.string.album_empty),color=Ink,fontSize=21.sp)
                    Text(stringResource(R.string.album_empty_hint),color=Muted,fontSize=16.sp)
                    Spacer(Modifier.height(24.dp)); Action(stringResource(R.string.draw_insect),true,click=newPaper)
                }
            } else {
                LazyVerticalGrid(columns=GridCells.Fixed(2),modifier=Modifier.weight(1f),horizontalArrangement=Arrangement.spacedBy(12.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
                    items(state.works,key={it.id}) { work ->
                        HoverSurface(shape=RoundedCornerShape(15.dp),borderWidth=if(work.id==selected?.id) 3.dp else 1.dp,
                            border=if(work.id==selected?.id) Accent else Panel,click={select(work.id)}) {
                        Column(Modifier.padding(7.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
                            ArtworkImage(state,work,Modifier.fillMaxWidth().aspectRatio(1f))
                            val name=stringResource(work.species.labelRes)
                            Text(if(work.id in state.gardenIds) stringResource(R.string.species_in_garden,name) else name,color=Ink,fontSize=15.sp)
                        }
                        }
                    }
                }
                selected?.let { work ->
                    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Panel).padding(10.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                        SpeciesIcon(work.species,Modifier.size(54.dp))
                        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                            Text(stringResource(work.species.labelRes),color=Ink,fontSize=19.sp,fontWeight=FontWeight.Bold)
                            Text(DateFormat.getDateTimeInstance(DateFormat.MEDIUM,DateFormat.SHORT,LocalConfiguration.current.locales[0]).format(Date(work.updatedAt)),color=Muted,fontSize=14.sp)
                        }
                        Action(stringResource(R.string.delete),enabled=!state.busy) { deleting=work }
                    }
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                        Action(stringResource(R.string.continue_drawing),enabled=!state.busy,modifier=Modifier.weight(1f),icon="crayon") { state.edit(work,editDone) }
                        Action(stringResource(R.string.preview),enabled=!state.busy,modifier=Modifier.weight(1f),icon="preview") { state.preview(work,preview) }
                    }
                    Action(stringResource(R.string.place_in_garden),true,!state.busy && state.pendingRelease==null,Modifier.fillMaxWidth(),icon="leaf") { state.place(work,enterGarden) }
                }
            }
            Text(state.message.localized(),color=Muted,fontSize=14.sp,maxLines=2)
        }
        deleting?.let { work -> Confirmation(stringResource(R.string.delete_title),stringResource(R.string.delete_message),{deleting=null}) {
            state.delete(work) { deleting=null; if(selectedId==work.id) select(null) }
        } }
    }
}

@Composable fun ArtworkImage(state: BugWorldState, work: Artwork, modifier: Modifier) {
    var loaded by remember(work.id,work.revision,work.templateVersion) { mutableStateOf(false) }
    val template=state.templateFor(work)
    val bitmap by produceState<Bitmap?>(null,work.id,work.revision,work.templateVersion) {
        value=withContext(Dispatchers.Default) { runCatching {
            val bytes=withContext(Dispatchers.IO) { state.store.image(work) }
            val decoded=BitmapFactory.decodeByteArray(bytes,0,bytes.size) ?: return@runCatching null
            try { template.bitmap(template.documentFrom(decoded,work.templateVersion),withOutline=true) }
            finally { decoded.recycle() }
        }.getOrNull() }
        loaded=true
    }
    Box(modifier.background(Panel),contentAlignment=Alignment.Center) {
        bitmap?.let { Image(it.asImageBitmap(),stringResource(work.species.labelRes),Modifier.fillMaxSize()) }
            ?: Text(if(loaded) stringResource(R.string.art_unreadable) else stringResource(R.string.art_loading),color=Muted,fontSize=14.sp)
    }
}
