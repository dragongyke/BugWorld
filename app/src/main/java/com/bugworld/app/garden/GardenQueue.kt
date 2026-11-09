package com.bugworld.app.garden

class GardenQueue(val capacity: Int = 10) {
    init { require(capacity > 0) }
    private val order = mutableListOf<String>()
    val ids: List<String> get() = order.toList()
    fun place(id: String) {
        require(id.isNotBlank())
        order.remove(id)
        order.add(id)
        while (order.size > capacity) order.removeAt(0)
    }
    fun remove(id: String) { order.remove(id) }
    fun restore(saved: List<String>, validIds: Set<String>) {
        order.clear()
        saved.filter { it in validIds }.forEach(::place)
    }
}
