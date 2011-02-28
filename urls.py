import os
from django.conf.urls.defaults import *

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),

    # Serving static files from the static directory
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': os.path.join(os.path.abspath(os.path.dirname(__file__)), "static")
    }),
)

urlpatterns += patterns('donate.views',
    ('^$', 'index'),
    (r'register$', 'register'),
    (r'account$', 'account'),
    (r'donate', 'donate'),
    (r'cancel_donation', 'cancel_donation'),
    (r'finish_donation', 'finish_donation'),
    (r'update_progress', 'update_progress'),
    (r'goal/(?P<slug>.*)$', 'view_application'),
    (r'application$', 'create_edit_application'),
    (r'application/(?P<app_id>\d+)$', 'create_edit_application'),

    (r'applications/(?P<app_id>\d+)/delete$', 'delete_application'),
    (r'signin$', 'signin'),
    (r'signout$', 'signout'),

    # XXX: A utility method for populating the database
    # with initial data. Remove this in production environment
    (r'bootstrap$', 'bootstrap'),
)
