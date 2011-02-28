# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
from djangoappengine.settings_base import *

import os

TIME_ZONE = 'America/Chicago'

SECRET_KEY = '=r-$b*8hglm+858&9t043hlm6-&6-3d3vfc4((7yd0dbrakhvi'

INSTALLED_APPS = (
    'djangoappengine',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'djangotoolbox',
    'django.contrib.webdesign',    
    'donate',
)

# This test runner captures stdout and associates tracebacks with their
# corresponding output. Helps a lot with print-debugging.
TEST_RUNNER = 'djangotoolbox.test.CapturingTestSuiteRunner'

ADMIN_MEDIA_PREFIX = '/media/admin/'
"""
STATICFILES_ROOT = os.path.abspath(os.path.dirname(__file__))
STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), 'static'),
)
STATICFILES_URL = '/static/'
MEDIA_URL = '/static/'
"""
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

ROOT_URLCONF = 'urls'

SITE_ID = 1

# Activate django-dbindexer if available
try:
    import dbindexer
    DATABASES['native'] = DATABASES['default']
    DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'native'}
    INSTALLED_APPS += ('dbindexer',)
except ImportError:
    pass

# NOTE: The emails below are test accounts to simulate a donation to a
# non-profit like the Red Cross. Ideally you would have a UI to help adding 
# new charities or provide a way for users creating applications to supply
# them. While in development you will need to create and use your own
# sandbox business accounts.
CHARITIES = [
    ("Boys and Girls Club of America", "char1_1298857996_biz@zaffra.com"),
    ("Red Cross", "char2_1298858296_biz@zaffra.com"),
    ("Wikipedia", "char3_1298858318_biz@zaffra.com"),
]

# PayPal-specific settings
# The comments for each setting should be sufficient, however, for
# a more in-depth discussion of PayPal and its APIs you should consult
# http://x.com as well as the AdaptivePayments documentation under
# the Documentation section on x.com.

##
# The endpoint we'll use for making payments through PayPal. During
# development, this will be the sandbox, however, you'll need to use
# the live API endpoint when real money needs to exchange hands. The
# live API is:
# https://svcs.paypal.com/AdaptivePayments/
#
# Remember, when operating in the sandbox you must be signed in to
# your PayPal developer account.
##
API_ENDPOINT = "https://svcs.sandbox.paypal.com/AdaptivePayments"

##
# Your API username
##
PAYPAL_USER_ID = "API Username from PayPal Sandbox"

##
# Your API password
##
PAYPAL_PASSWORD = "API Password from PayPal Sandbox"

##
# Your API signature, which is required only if you use 3-token
# authorization; a certificate does not use a signature
##
PAYPAL_SIGNATURE = "API Signature from PayPal Sandbox"

##
# Your application's identification, which is issued by PayPal. Here we are using
# the standard test application ID provided by PayPal for all development
##
PAYPAL_APPLICATION_ID = "APP-80W284485P519543T"

##
# Specify the request and response formats to be JSON. You can
# modify these to be NV or XML, however, no code to support any
# request or response other JSON exists in the current 
# implementation.
## 
PAYPAL_REQUEST_DATA_FORMAT = "JSON"
PAYPAL_RESPONSE_DATA_FORMAT = "JSON"

##
# URLs for successful and canceled transactions. These are used by PayPal
# when redirecting back to our site.
##
RETURN_URL = "http://localhost:8081/finish_donation?payKey=${payKey}"
CANCEL_URL = "http://localhost:8081/cancel_donation?payKey=${payKey}"

