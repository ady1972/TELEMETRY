# V0.1.3 - SQLite thread fix

Crash diagnostic received on Android:

`ProgrammingError: SQLite objects created in a thread can only be used in that same thread`

Cause: `SessionStore` opened SQLite while `PythonBridge` was initialized, then Compose called the bridge from `Dispatchers.IO`, which may use a different worker thread.

Fix:
- SQLite connection opened with `check_same_thread=False`.
- Every database access is serialized with a Python `threading.RLock`.
- Reads and writes can therefore be invoked safely by Android coroutines which move between IO worker threads.
- SAFE BOOT remains enabled for this validation release.

Host verification: 100 `sessions()` calls executed successfully across 8 worker threads using the same `SessionStore` instance.
