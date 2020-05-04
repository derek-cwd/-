from django.conf.urls import re_path

from . import views

urlpatterns = [
    re_path('^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
    re_path('^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    re_path('^register/$', views.RegisterView.as_view()),
    re_path('^login/$', views.LoginView.as_view()),
    re_path('^logout/$', views.LogoutView.as_view()),
    re_path('^info/$', views.UserInfoView.as_view()),
    re_path('^email/$', views.EmailView.as_view()),
    re_path('^emails/verification/$', views.VerifyEmailView.as_view()),

]