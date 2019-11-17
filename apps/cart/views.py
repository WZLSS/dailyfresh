from django.shortcuts import render
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
# Create your views here.
from django.views import View


class CartAddView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errorMsg': '请登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errorMsg': '数据不完整'})
        # 校验商品数量
        try:
            count = int(count)
        except Exception as result:
            return JsonResponse({'res': 2, 'errorMsg': '商品数量出错'})
        # 校验商品sku_id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errorMsg': "商品不存在"})
        # 添加购物车记录
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')
        cart_count = conn.hget(cart_key, sku_id)
        # 判断购物车里是否存在相同sku_id的商品，如果存在数量累加
        if cart_count:
            count += int(cart_count)
        # 比较库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errorMsg': '库存不足'})
        # 设置redis中的count值
        conn.hset(cart_key, sku_id, count)
        # 获取购物车中条目数
        total_count = conn.hlen(cart_key)
        return JsonResponse({'res': 5, 'errorMsg': '添加成功', 'total_count': total_count})


class CartInfoView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')
        # 获取购物车商品信息
        cart_dict = conn.hgetall(cart_key)
        skus = []
        # 保存购物车种商品总数目和总价格
        total_count = 0
        total_price = 0
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            amount = sku.price*int(count)
            # 动态增加属性
            sku.amount = amount
            sku.count = int(count)
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        context = {'skus': skus, 'total_count': total_count, 'total_price': total_price}
        return render(request, 'cart.html', context)


class CartUpdateView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errorMsg': '请登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errorMsg': '数据不完整'})
        # 校验商品数量
        try:
            count = int(count)
        except Exception as result:
            return JsonResponse({'res': 2, 'errorMsg': '商品数量出错'})
        # 校验商品sku_id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errorMsg': "商品不存在"})
        # 添加购物车记录
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')
        # 比较库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errorMsg': '库存不足'})
        # 更新redis中的count值
        conn.hset(cart_key, sku_id, count)
        # 获取redis中商品总数目
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        return JsonResponse({'res': 5, 'total_count': total_count, 'errorMsg': '更新成功'})


class CartDelView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errorMsg': '请登录'})
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': 1, 'errorMsg': '数据不完整'})
        # 校验商品sku_id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errorMsg': "商品不存在"})
        # 删除购物车记录
        cart_key = 'cart_%d' % user.id
        conn = get_redis_connection('default')
        conn.hdel(cart_key, sku_id)
        # 获取redis中商品总数目
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        return JsonResponse({'res': 3, 'total_count': total_count, 'errorMsg': "删除失败"})
