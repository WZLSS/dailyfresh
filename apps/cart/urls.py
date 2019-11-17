from django.urls import path, re_path
from apps.cart.views import CartAddView, CartInfoView, CartUpdateView, CartDelView

app_name = 'cart'
urlpatterns = [
    re_path(r'^add$', CartAddView.as_view(), name='add'),
    re_path(r'^$', CartInfoView.as_view(), name='show'),
    re_path(r'^update$', CartUpdateView.as_view(), name='update'),
    re_path(r'^del$', CartDelView.as_view(), name='del')
]
