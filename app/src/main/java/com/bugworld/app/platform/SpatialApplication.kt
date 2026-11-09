package com.bugworld.app.platform

import android.app.Application
import com.pico.spatial.ui.foundation.dsl.launch
import com.bugworld.app.mainApp
import com.bugworld.app.BugWorldState

class SpatialApplication : Application() {
    lateinit var state: BugWorldState
        private set
    override fun onCreate() {
        super.onCreate()
        state = BugWorldState(this)
        launch(::mainApp)
    }
}
