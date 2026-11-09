package com.bugworld.app.garden

class Population(private val capacity: Int) {
    data class Entry(var age: Float=0f,var retiring: Float=0f,var leaving: Boolean=false)
    val entries=linkedMapOf<String,Entry>()
    fun tick(desired: List<String>,delta: Float) {
        val wanted=desired.distinct().takeLast(capacity)
        val iterator=entries.iterator()
        while(iterator.hasNext()) {
            val (id,entry)=iterator.next()
            entry.age+=delta
            entry.leaving=id !in wanted
            entry.retiring=if(entry.leaving) entry.retiring+delta else 0f
            if(entry.retiring>=1.2f) iterator.remove()
        }
        wanted.forEach { id -> if(id !in entries && entries.size<capacity) entries[id]=Entry() }
    }
}
