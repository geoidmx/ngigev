from .base import *

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

# Take environment variables from .env file
environ.Env.read_env(BASE_DIR / '../.env')

# SECURITY WARNING: keep the secret key used in production secret!
#SECRET_KEY = 'django-insecure-x_=^w(-5d9d+1k-es2*hwk7n4q6=$a9b3f^0pza%x1*$2j37gf'
# exception if SECRET_KEY not in os.environ
SECRET_KEY = env('SECRET_KEY')

# False if not in os.environ because of casting above
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

DATABASES = {
    # The db() method is an alias for db_url().
    'default': env.db('DATABASE_URL'),
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = ( BASE_DIR / "../static" )

STATICFILES_DIRS = [
    BASE_DIR / "../static/assets",
    BASE_DIR / "../static/src",
]

MEDIA_URL = '/media/'
MEDIA_ROOT = ( BASE_DIR / "../media" )