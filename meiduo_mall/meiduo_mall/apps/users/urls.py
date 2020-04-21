from django.conf.urls import re_path

from . import views

urlpatterns = [
    re_path('^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
re_path('^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
]