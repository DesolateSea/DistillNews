"""Backward-compatibility shim — re-exports FileStore from its new location.

The canonical module is now ``service.db.filestore``.  This file ensures that
any existing ``from service.db.storage import FileStore`` continues to work.
"""

from service.db.filestore import FileStore  # noqa: F401
