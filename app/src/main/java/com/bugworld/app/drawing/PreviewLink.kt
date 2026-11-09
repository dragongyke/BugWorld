package com.bugworld.app.drawing

import com.bugworld.app.data.Species

class PreviewLink {
    private var draft: Species?=null
    private var saved: String?=null
    private var revision=0
    fun matchesDraft(species: Species,version: Int): Boolean = draft==species && revision==version
    fun matchesSaved(id: String,version: Int): Boolean = saved==id && revision==version
    fun draft(species: Species,version: Int) { draft=species; saved=null; revision=version }
    fun saved(id: String,version: Int) { saved=id; draft=null; revision=version }
    fun changedDraft(species: Species,version: Int): Boolean {
        if(draft!=species || revision==version) return false
        revision=version; return true
    }
    fun changedSaved(id: String,version: Int): Boolean {
        if(saved!=id || revision==version) return false
        revision=version; return true
    }
    fun clear(id: String): Boolean { if(saved!=id) return false; saved=null; return true }
}
