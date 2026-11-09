package com.bugworld.app.data
import kotlinx.coroutines.CancellationException

object DraftWrite {
    suspend fun attempt(write: suspend ()->Unit,onFailure: (Exception)->Unit): Boolean {
        return try { write(); true } catch(error: Exception) {
            if(error is CancellationException) throw error
            onFailure(error)
            false
        }
    }
}
