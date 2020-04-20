from django.conf.urls import re_path

from . import views

urlpatterns = [
    re_path('^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
]