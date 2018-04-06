""" advanced client urls """
from django.conf.urls import url
from .views import (VocalSaparateAPIView, PitchGuideAPIView)

urlpatterns = [
    url(r'^vocal-separator/$', VocalSaparateAPIView.as_view()),
    url(r'^pitch-guide/$', PitchGuideAPIView.as_view()),
    ]
 