from rest_framework.routers import DefaultRouter
from apps.core.views.attachment import AttachmentViewSet

router = DefaultRouter()
router.register(r'attachments', AttachmentViewSet, basename='attachment')

urlpatterns = router.urls
