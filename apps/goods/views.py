from django.shortcuts import render, redirect
from django.urls import reverse
from apps.goods.models import IndexTypeGoodsBanner, IndexPromotionBanner, GoodsType, IndexGoodsBanner, GoodsSKU
from apps.order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.cache import cache
from django.core.paginator import Paginator
# Create your views here.
from django.views import View


# 主页
class IndexView(View):
    def get(self, request):
        # 尝试从缓存中获取数据，若没有数据，返回None
        context = cache.get('context')
        if context is None:
            # print("设置缓存")
            # 获取首页展示商品品类信息
            types = GoodsType.objects.all()
            # 获取首页轮播商品信息
            good_banners = IndexGoodsBanner.objects.all().order_by('index')  # order_by默认升序排列，-index实现降序排列
            # 获取首页促销商品信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
            # 获取首页分类商品信息, 分为按图片展示或标题展示
            for type in types:
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
                #     动态增加属性
                type.image_banners = image_banners
                type.title_banners = title_banners

            # 设置页面缓存
            context = {'types': types, 'good_banners': good_banners, 'promotion_banners': promotion_banners}
            cache.set('context', context, 3600)
        # 获取购物车商品总数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            cart_key = 'cart_%d' % user.id
            # 获取redis的连接
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)
        # 更新字典数据
        context.update(cart_count=cart_count)
        return render(request, 'index.html', context)


# 详情页
class DetailView(View):
    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            redirect(reverse('goods:index'))
        # 获取品种列表
        types = GoodsType.objects.all()
        # 获取评论信息,过滤掉评论信息为空的
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        # 获取新品信息,并降序排列,并只显示两个
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取相同spu的商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        # 获取购物车商品总数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            cart_key = 'cart_%d' % user.id
            # 获取redis的连接
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)
            #  设置用户历史浏览记录
            # conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            conn.lrem(history_key, 0, goods_id)  # 0代表移除表中所有与 VALUE 相等的值
            #  从左侧插入goods_id
            conn.lpush(history_key, goods_id)
            #  只保存5条记录
            conn.ltrim(history_key, 0, 4)
        context = {'sku': sku, 'types': types, 'sku_orders': sku_orders, 'new_skus': new_skus, 'cart_count': cart_count, 'same_spu_skus': same_spu_skus}
        return render(request, 'detail.html', context)


# 列表页 访问格式 /list/品类id/页码?排序方式
class ListView(View):
    def get(self, request, type_id, page):
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取此种类下的所有商品, 并按指定排序方式排序
        sort = request.GET.get('sort')
        if sort == 'sales':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        elif sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        else:
            sort='default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 获取所有品种信息
        types = GoodsType.objects.all()
        # 分页
        paginator = Paginator(skus, 1)
        # 获取指定页的内容
        try:
            page = int(page)
        except Exception as result:
            page = 1
        # 获取page页内容的Page对象
        sku_page = paginator.page(page)
        # 进行页码的控制，使其只显示5个页码
        num_pages = paginator.num_pages
        # 总页数小于5，显示所有
        if num_pages < 5:
            pages = range(1, num_pages+1)
        # 当前页小于3，显示前五页
        elif page <= 3:
            pages = range(1, 6)
        # 当前页大于3，显示后5页
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        # 显示前两页，当前页，后两页
        else:
            pages = range(page-2, page+3)
        # 获取购物车数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            cart_key = 'cart_%d' % user.id
            # 获取redis的连接
            conn = get_redis_connection('default')
            cart_count = conn.hlen(cart_key)
        # 获取新品信息,并降序排列,并只显示两个
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]
        context = {'type': type, 'types': types, 'sku_page': sku_page, 'cart_count': cart_count, 'new_skus': new_skus, 'sort': sort}
        return render(request, 'list.html', context)