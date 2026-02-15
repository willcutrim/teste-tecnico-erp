from config.settings import *
import os


# Usa MySQL do Docker para testes
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DATABASE', 'erp_pedidos'),
        'USER': os.environ.get('MYSQL_USER', 'erp_user'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD', 'erp_password'),
        'HOST': os.environ.get('MYSQL_HOST', 'mysql'),
        'PORT': os.environ.get('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
        'TEST': {
            'NAME': 'test_erp_pedidos',
        },
    }
}


# Desabilita cache Redis para testes
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# Desabilita throttling para testes
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}


# Desabilita migrações para testes mais rápidos
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()


# Password hasher mais rápido para testes
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
