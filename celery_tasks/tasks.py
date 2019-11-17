# 使用celery
from django.core.mail import send_mail
from django.conf import settings
from celery import Celery
from django.template import loader, RequestContext
from django.http import request

# 在任务处理者一端加这几句
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
django.setup()

from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.139.132:6379/1')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a ' \
                   'href="http://192.168.139.132:8000/user/active/%s">点击我激活账号</a>' % (username, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def generate_static_index_html():
    # 生成静态页面
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
        #  动态增加属性
        type.image_banners = image_banners
        type.title_banners = title_banners
    # 获取购物车商品总数量
    context = {'types': types, 'good_banners': good_banners, 'promotion_banners': promotion_banners
               }
    # 加载模板文件，定义模板对象
    temp = loader.get_template('static_index.html')
    # 定义模板上下文
    # RequestContext(request, context)
    # 模板渲染
    static_index_html = temp.render(context)
    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    # 创建文件
    with open(save_path, 'w') as f:
        f.write(static_index_html)
