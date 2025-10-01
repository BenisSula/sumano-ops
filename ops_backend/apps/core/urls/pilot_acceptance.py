"""
URL patterns for the pilot acceptance module.
"""
from rest_framework.routers import DefaultRouter
from apps.core.views.pilot_acceptance import PilotAcceptanceViewSet

router = DefaultRouter()
router.register(r'pilot-acceptance', PilotAcceptanceViewSet, basename='pilot-acceptance')

urlpatterns = router.urls
