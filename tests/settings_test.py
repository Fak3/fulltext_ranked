import environ

env = environ.Env()

SRC_DIR = environ.Path(__file__) - 1  # src/
env.read_env(SRC_DIR('env-localtest'))  # overrides env-local

from settings import *

RAISE_404 = True

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

#EMAIL_BACKEND = 'eml_email_backend.EmailBackend'
##EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = SRC_DIR('eml_mails')

ADMIN_EMAIL = 'test@example.com'

# Speedup login during tests.
PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)


# NOTE: Default django staticfiles app should be disabled in tests due to
# conflict with whitenoise in pytest-django live_server.
INSTALLED_APPS.remove('django.contrib.staticfiles')


REST_FRAMEWORK = {
    ## 'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'EXCEPTION_HANDLER': lambda *a: None,  # raise validation exceptions during tests.
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
}


#update(LOGGING, {
    #'loggers': {
        #'django.db.backends': {'level': 'ERROR'},  # Prevent flood when assertNumQueries() called
    #}
#})

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
    #'default': {
        # TODO: check 'lrucache_backend.LRUObjectCache'

        # NOTE: deprecated?
        #'BACKEND': 'test.cache_backend.LocMemNoPickleCache',  # This backend can store Mock.
    #}
}

