# Import route files FIRST (they register decorators on the shared api)
from . import partner
from . import order

# Then register the controller AFTER all routes are collected
from .app import api

api.register()
