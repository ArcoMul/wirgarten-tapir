"""
Django settings for tapir project.

Generated by 'django-admin startproject' using Django 3.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import email.utils
import os
from pathlib import Path

import celery.schedules
import environ

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str(
    "SECRET_KEY", default="fl%20e9dbkh4mosi5$i$!5&+f^ic5=7^92hrchl89x+)k0ctsn"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

TAPIR_VERSION = env.str("TAPIR_VERSION", default="dev")
if not DEBUG:
    print(
        f"Tapir Version: {TAPIR_VERSION}"
        if TAPIR_VERSION
        else "\033[93m>>> WARNING: TAPIR_VERSION is not set, cache busting will not work!\033[0m"
    )

ERROR_LOG_DIR = env.str("ERROR_LOG_DIR", default="error_logs")

### WIRGARTEN CONFIG ###

COOP_SHARE_PRICE = 50.0

##########################

ENABLE_SILK_PROFILING = False

# Application definition
INSTALLED_APPS = [
    # Must come before contrib.auth to let the custom templates be discovered for auth views
    "tapir.accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django_bootstrap5",
    "bootstrap_datepicker_plus",
    "tapir.core",
    "tapir.log",
    "tapir.utils",
    "tapir.wirgarten",
    "tapir.configuration",
    "django_tables2",
    "django_filters",
    "django_select2",  # For autocompletion in form fields
    "phonenumber_field",
    "localflavor",
    # TODO(Leon Handreke): Don't install in prod
    "django_extensions",
    "formtools",
]

if ENABLE_SILK_PROFILING:
    INSTALLED_APPS.append("silk")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tapir.accounts.models.language_middleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "tapir.accounts.middleware.KeycloakMiddleware",
    "tapir.wirgarten.error_middleware.GlobalServerErrorHandlerMiddleware",
]

X_FRAME_OPTIONS = "ALLOWALL"
XS_SHARING_ALLOWED_METHODS = ["POST", "GET", "OPTIONS", "PUT", "DELETE"]

if ENABLE_SILK_PROFILING:
    MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + MIDDLEWARE

ROOT_URLCONF = "tapir.urls"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "tapir/templates")],
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

WSGI_APPLICATION = "tapir.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    "default": env.db(default="postgresql://tapir:tapir@db:5432/tapir"),
}

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://redis:6379")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://redis:6379")
CELERY_BEAT_SCHEDULE = {
    "export_supplier_list_csv": {
        "task": "tapir.wirgarten.tasks.export_supplier_list_csv",
        "schedule": celery.schedules.crontab(
            day_of_week="tuesday",
            minute=0,
            hour=0
            # once a week, Tuesday at 00:00
        ),
    },
    "export_pick_list_csv": {
        "task": "tapir.wirgarten.tasks.export_pick_list_csv",
        "schedule": celery.schedules.crontab(
            day_of_week="tuesday",
            minute=0,
            hour=0
            # once a week, Tuesday at 00:00
        ),
    },
    "export_sepa_payments": {
        "task": "tapir.wirgarten.tasks.export_sepa_payments",
        "schedule": celery.schedules.crontab(
            day_of_month=15,
            minute=0,
            hour=0
            # once a month, on 15th 0:00
        ),
    },
    "export_harvest_share_subscriber_emails": {
        "task": "export_harvest_share_subscriber_emails",
        "schedule": celery.schedules.crontab(day_of_week="monday", minute=0, hour=0),
    },
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
PASSWORD_RESET_TIMEOUT = (
    7776000  # 90 days, so that the welcome emails stay valid for long enough
)

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# django-environ EMAIL_URL mechanism is a bit hairy with passwords with slashes in them, so use this instead
EMAIL_ENV = env("EMAIL_ENV", default="dev")
if EMAIL_ENV == "dev":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_HOST_SENDER = "dev@example.com"
elif EMAIL_ENV == "test":
    # Local SMTP
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
elif EMAIL_ENV == "prod":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env.str("EMAIL_HOST")
    EMAIL_HOST_SENDER = env.str("EMAIL_HOST_SENDER")
    EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
    EMAIL_PORT = env.str("EMAIL_PORT", default=587)
    # the next 2 options are mutually exclusive!
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
    EMAIL_AUTO_BCC = env.str("EMAIL_AUTO_BCC")

# DJANGO_ADMINS="Blake <blake@cyb.org>, Alice Judge <alice@cyb.org>"
ADMINS = tuple(email.utils.parseaddr(x) for x in env.list("DJANGO_ADMINS", default=[]))
# Crash emails will come from this address.
SERVER_EMAIL = env("SERVER_EMAIL", default="tapir@foodcoopx.de")

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

SELECT2_JS = "core/select2/4.0.13/js/select2.min.js"
SELECT2_CSS = "core/select2/4.0.13/css/select2.min.css"
SELECT2_I18N_PATH = "core/select2/4.0.13/js/i18n"

WEASYPRINT_BASEURL = "/"

AUTH_USER_MODEL = "accounts.TapirUser"
# LOGIN_REDIRECT_URL = "index"
LOGIN_URL = "login"

SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")

PHONENUMBER_DEFAULT_REGION = "DE"

LOCALE_PATHS = [os.path.join(BASE_DIR, "tapir/translations/locale")]

if ENABLE_SILK_PROFILING:
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_BINARY = True
    SILKY_META = True

KEYCLOAK_ADMIN_CONFIG = dict(
    SERVER_URL=env.str("KEYCLOAK_ADMIN_SERVER_URL", default="http://keycloak:8080"),
    PUBLIC_URL=env.str("KEYCLOAK_PUBLIC_URL", default="http://localhost:8080"),
    CLIENT_ID=env.str("KEYCLOAK_CLIENT_ID", default="tapir-backend"),
    FRONTEND_CLIENT_ID=env.str("KEYCLOAK_FRONTEND_CLIENT_ID", default="tapir-frontend"),
    REALM_NAME=env.str("KEYCLOAK_ADMIN_REALM_NAME", default="master"),
    USER_REALM_NAME=env.str("KEYCLOAK_ADMIN_USER_REALM_NAME", default="tapir"),
    CLIENT_SECRET_KEY=env.str("KEYCLOAK_ADMIN_CLIENT_SECRET_KEY", default="**********"),
)

CSP_FRAME_SRC = ["'self'", KEYCLOAK_ADMIN_CONFIG["PUBLIC_URL"]]

# these are keycloak internal roles and will be filtered out automatically when fetching roles
KEYCLOAK_NON_TAPIR_ROLES = [
    "offline_access",
    "uma_authorization",
    "default-roles-tapir",
]

# The link above contains all settings
BOOTSTRAP_DATEPICKER_PLUS = {
    "options": {
        "locale": "de",
        "showClose": True,
        "showClear": True,
        "showTodayButton": True,
        "allowInputToggle": True,
    },
    "variant_options": {
        "date": {
            "format": "DD.MM.YYYY",
        },
        "datetime": {
            "format": "DD.MM.YYYY HH:mm",
        },
    },
}
