from django.contrib import admin
from django.core.cache import cache
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, Goods, \
    GoodsImage, GoodsSKU


# Register your models here.


class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        #  新增或修改表中数据时调用
        super().save_model(request, obj, form, change)
        from celery_tasks.tasks import generate_static_index_html
        # 发布任务，celery执行
        generate_static_index_html.delay()
        # 清除缓存
        cache.delete('context')

    def delete_model(self, request, obj):
        #  删除数据时调用
        super().delete_model(request, obj)
        from celery_tasks.tasks import generate_static_index_html
        # 发布任务，celery执行
        generate_static_index_html.delay()
        # 清除缓存
        cache.delete('context')


class GoodsTypeAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass


class GoodsAdmin(BaseModelAdmin):
    pass


class GoodsImageAdmin(BaseModelAdmin):
    pass


class GoodsSKUAdmin(BaseModelAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(GoodsImage, GoodsImageAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
