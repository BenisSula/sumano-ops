"""
URL patterns for the pilot handover module.
"""
from rest_framework.routers import DefaultRouter
from apps.core.views.pilot_handover import PilotHandoverViewSet

router = DefaultRouter()
router.register(r'pilot-handover', PilotHandoverViewSet, basename='pilot-handover')

urlpatterns = router.urls
