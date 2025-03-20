"""
Django settings for mi_proyecto project.

Generado por 'django-admin startproject' usando Django 5.1.7.
Documentación de Django: https://docs.djangoproject.com/en/5.1/
"""

import os
from pathlib import Path

# Ruta base del proyecto (un nivel arriba de este archivo settings.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------
# CONFIGURACIÓN DE SEGURIDAD
# --------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
# Es recomendable en producción obtener el SECRET_KEY desde una variable de entorno
# Para Render, por ejemplo:
# SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-insegura-de-desarrollo')
SECRET_KEY = "django-insecure-d5#_gt$@@_bb3yw2_fb(9wd$q^f&0t7qg86q^xx#uqh&$8ze@("

# En producción, se recomienda poner DEBUG = False
DEBUG = True

# Ajustar para que contenga el host de tu despliegue
ALLOWED_HOSTS = ['miapp.onrender.com', '127.0.0.1', 'localhost']
# Si vas a usar Render, coloca el dominio real que te asigna:
# ALLOWED_HOSTS = ['mi-app.onrender.com', ...]


# --------------------------------------------------------------------
# APLICACIONES INSTALADAS
# --------------------------------------------------------------------
INSTALLED_APPS = [
    # Aplicaciones de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tu aplicación principal
    'cuestionario',
]


# --------------------------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # En producción podrías usar WhiteNoise para servir estáticos
    # 'whitenoise.middleware.WhiteNoiseMiddleware',

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# --------------------------------------------------------------------
# URLS Y WSGI
# --------------------------------------------------------------------
ROOT_URLCONF = "mi_proyecto.urls"

WSGI_APPLICATION = "mi_proyecto.wsgi.application"


# --------------------------------------------------------------------
# TEMPLATES
# --------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Si deseas usar una carpeta "templates" global, configúrala aquí:
        # "DIRS": [BASE_DIR / "templates"],
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# --------------------------------------------------------------------
# BASE DE DATOS
# --------------------------------------------------------------------
# Para cambiar a PostgreSQL u otra BD en producción, configura aquí:
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# --------------------------------------------------------------------
# VALIDACIÓN DE CONTRASEÑAS
# --------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# --------------------------------------------------------------------
# INTERNACIONALIZACIÓN Y ZONA HORARIA
# --------------------------------------------------------------------
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS
# --------------------------------------------------------------------
# URL base para archivos estáticos
STATIC_URL = '/static/'

# Carpeta física donde se recopilarán los archivos estáticos en producción
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Si tienes archivos estáticos adicionales en una carpeta "static" dentro de tu app:
# STATICFILES_DIRS = [
#     BASE_DIR / 'static'
# ]

# Con 'DEBUG = False', necesitarás que un servidor real (o whitenoise) sirva el contenido de STATIC_ROOT.
# Si activas whitenoise.middleware, también puedes habilitar:
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# --------------------------------------------------------------------
# TIPO DE CAMPO AUTOINCREMENTAL POR DEFECTO
# --------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
