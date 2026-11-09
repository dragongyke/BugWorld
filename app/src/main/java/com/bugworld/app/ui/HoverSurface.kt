package com.bugworld.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.pico.spatial.ui.foundation.hover.*

/** Gaze hover is rendered by the compositor, never inferred from in-process pointer hover. */
@Composable fun HoverSurface(
    modifier: Modifier=Modifier,
    enabled: Boolean=true,
    shape: RoundedCornerShape=RoundedCornerShape(16.dp),
    background: Color=Panel,
    border: Color=Color.Transparent,
    borderWidth: Dp=1.dp,
    highlight: Color=Lavender.copy(alpha=.65f),
    click: ()->Unit,
    content: @Composable BoxScope.()->Unit,
) {
    val group=remember { SpatialHoverEffectGroup.obtain() }
    val interaction=remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    Box(modifier.spatialHoverEffectGroup(group,enable=enabled)
        .spatialHoverEffect { hover ->
            animation(tween(durationMillis=110)) { scale(if(enabled && hover.isActive) 1.045f else 1f) }
        }
        .clip(shape).background(if(pressed && enabled) Accent.copy(alpha=.65f) else background)
        .border(borderWidth,border,shape)
        .clickable(interactionSource=interaction,indication=null,enabled=enabled,onClick=click),
        contentAlignment=Alignment.Center) {
        // A grouped responder lights the whole target, including its edges, without intercepting input.
        Box(Modifier.matchParentSize()
            .spatialHoverEffectGroup(group.behavior(SpatialHoverEffectGroup.Behavior.Responder),enable=enabled)
            .spatialHoverEffect { hover ->
                animation(tween(durationMillis=100)) { alpha(if(enabled && hover.isActive) 1f else 0f) }
            }
            .background(highlight,shape).border(3.dp,Accent,shape))
        content()
    }
}
