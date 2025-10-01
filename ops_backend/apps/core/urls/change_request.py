"""
URL patterns for the change request module.
"""
from rest_framework.routers import DefaultRouter
from apps.core.views.change_request import ChangeRequestViewSet

router = DefaultRouter()
router.register(r'change-requests', ChangeRequestViewSet, basename='change-request')

urlpatterns = router.urls
