from django.urls import path, re_path
from apps.order.views import OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckView, OrderCommentView

app_name = 'order'
urlpatterns = [
    re_path(r'^place$', OrderPlaceView.as_view(), name='place'),
    re_path(r'^commit$', OrderCommitView.as_view(), name='commit'),
    re_path(r'^pay$', OrderPayView.as_view(), name='pay'),
    re_path(r'^check$', OrderCheckView.as_view(), name='check'),
    re_path(r'^comment/(?P<order_id>.+)$', OrderCommentView.as_view(), name='comment'),
]
