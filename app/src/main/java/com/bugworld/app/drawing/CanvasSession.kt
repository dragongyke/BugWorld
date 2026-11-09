package com.bugworld.app.drawing

import com.bugworld.app.data.Species

/** Only explicit album edits load saved art. This cache lasts for one application session. */
class CanvasSession(papers: Map<Species,PaintDocument>) {
    data class Entry(val document: PaintDocument, val artworkId: String? = null)
    private val entries = papers.mapValues { Entry(it.value) }.toMutableMap()
    var species = Species.BUTTERFLY; private set
    val current get() = entries.getValue(species)
    fun restart() {
        entries.replaceAll { _,entry -> Entry(entry.document.blankCopy()) }
        species=Species.BUTTERFLY
    }
    fun select(next: Species) { require(next in entries); species=next }
    fun fresh() { entries[species]=Entry(current.document.blankCopy()) }
    fun saved(id: String) { entries[species]=current.copy(artworkId=id) }
    fun edit(kind: Species,document: PaintDocument,id: String) {
        entries[kind]=Entry(document,id); species=kind
    }
    fun deleted(id: String) {
        entries.replaceAll { _,entry -> if(entry.artworkId==id) entry.copy(artworkId=null) else entry }
    }

    /** Eight edited sheets share the former four-sheet undo budget. Keep the active sheet's history first. */
    fun trimHistory(budgetBytes: Long = 128L * 1024 * 1024) {
        require(budgetBytes >= 0)
        val docs=entries.values.map { it.document }
        var bytes=docs.sumOf { it.historyBytes }
        while (bytes>budgetBytes) {
            val victim=docs.filter { it!==current.document && it.historyBytes>0 }.maxByOrNull { it.historyBytes }
                ?: current.document
            val previous=victim.historyBytes
            victim.discardDistantHistory()
            bytes-=previous-victim.historyBytes
        }
    }
}
