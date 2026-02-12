from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet

router = DefaultRouter()
router.register('customers', ClienteViewSet, basename='customers')

urlpatterns = router.urls
