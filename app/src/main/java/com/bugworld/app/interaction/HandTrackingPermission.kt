package com.bugworld.app.interaction

import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner

private const val HAND_PERMISSION="com.picovr.permission.HAND_TRACKING"

/** Request once per Stage visit, and recheck when returning from system settings. */
@Composable internal fun rememberHandTrackingPermission(visible: Boolean): Boolean {
    val context=LocalContext.current
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    fun isGranted()=ContextCompat.checkSelfPermission(context,HAND_PERMISSION)==PackageManager.PERMISSION_GRANTED
    var granted by remember { mutableStateOf(isGranted()) }
    var requested by rememberSaveable { mutableStateOf(false) }
    val launcher=rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted=it }
    DisposableEffect(lifecycle,context) {
        val observer=LifecycleEventObserver { _,event ->
            if(event==Lifecycle.Event.ON_RESUME) granted=isGranted()
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    LaunchedEffect(visible) {
        granted=isGranted()
        if(visible && !granted && !requested) {
            requested=true
            launcher.launch(HAND_PERMISSION)
        }
    }
    return granted
}
