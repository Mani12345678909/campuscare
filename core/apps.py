from django.apps import AppConfig
from django.db.backends.signals import connection_created


def enable_sqlite_foreign_keys(sender, connection, **kwargs):
    """
    Ensure SQLite enforces foreign key constraints per the requirement.
    """
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        connection_created.connect(enable_sqlite_foreign_keys)
