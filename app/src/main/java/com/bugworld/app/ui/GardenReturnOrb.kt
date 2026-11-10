package com.bugworld.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.*
import androidx.compose.ui.res.stringResource
import com.bugworld.app.R
import com.pico.spatial.ui.design.Text
import com.pico.spatial.ui.foundation.hover.*

/** Transparent icon/label over a real sphere, world-fixed with the garden. No rectangular toolbar. */
@Composable fun GardenReturnOrb(enabled: Boolean,exit: ()->Unit) {
    val orbLabel=stringResource(R.string.return_orb)
    val group=remember { SpatialHoverEffectGroup.obtain() }
    Column(Modifier.size(200.dp,144.dp),horizontalAlignment=Alignment.CenterHorizontally) {
        Text(stringResource(R.string.return_canvas),color=Color(0xFFFFF3D6),fontSize=17.sp,
            modifier=Modifier.background(Color(0xDD253D32), CircleShape)
                .clickable(enabled=enabled,onClick=exit).padding(horizontal=12.dp,vertical=4.dp))
        Spacer(Modifier.height(12.dp))
        Box(Modifier.size(78.dp).semantics { contentDescription=orbLabel }
            .spatialHoverEffectGroup(group,enable=enabled)
            .spatialHoverEffect { hover -> animation(tween(durationMillis=160)) { scale(if(hover.isActive && enabled) 1.10f else 1f) } }
            .background(Brush.radialGradient(listOf(Color(0x77FFF2C7),Color(0x333D7353),Color.Transparent)),CircleShape)
            .clickable(enabled=enabled,onClick=exit),contentAlignment=Alignment.Center) {
            Box(Modifier.matchParentSize()
                .spatialHoverEffectGroup(group.behavior(SpatialHoverEffectGroup.Behavior.Responder))
                .spatialHoverEffect { hover -> animation(tween(durationMillis=120)) { alpha(if(hover.isActive && enabled) 1f else 0f) } }
                .border(2.dp,Color(0xFFE6F9FF),CircleShape))
            LineIcon("crayon",Modifier.size(30.dp),color=Color.White)
        }
    }
}
