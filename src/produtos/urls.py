from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet

router = DefaultRouter()
router.register('products', ProdutoViewSet, basename='products')

urlpatterns = router.urls
