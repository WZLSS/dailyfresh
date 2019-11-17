from django.http import JsonResponse
from django.shortcuts import render, redirect
from apps.goods.models import GoodsSKU
from django.urls import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from apps.user.models import Address
from utils.mixin import LoginRequiredMixin
from apps.order.models import OrderInfo, OrderGoods
from datetime import datetime
from django.db import transaction
from alipay import AliPay
from django.conf import settings
import os
import time


class OrderPlaceView(LoginRequiredMixin, View):
    def post(self, request):
        sku_ids = request.POST.getlist('sku_ids')
        user = request.user
        cart_key = 'cart_%d' % user.id
        if not sku_ids:
            return render(reverse('cart:show'))
        conn = get_redis_connection('default')
        # 遍历ids
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取商品数量
            count = conn.hget(cart_key, sku_id)
            # 计算小计
            amount = sku.price * int(count)
            sku.count = int(count)
            sku.amount = amount
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        # 运费
        transit_price = 10
        # 总金额
        total_money = total_price + transit_price
        # 获取收货地址
        addrs = Address.objects.filter(user=user)
        sku_ids = ','.join(sku_ids)
        # 组织上下文
        context = {'skus': skus, 'sku_ids': sku_ids, 'total_count': total_count, 'addrs': addrs,
                   'total_price': total_price, 'transit_price': transit_price, 'total_money': total_money}
        return render(request, 'place_order.html', context)


class OrderCommitView(View):
    # 开启事务
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errorMsg': "请登录"})
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errorMsg': "数据不完整"})
        if pay_method not in OrderInfo.PAY_METHOD.keys():
            return JsonResponse({'res': 2, 'errorMsg': "支付方式不存在"})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errorMsg': "收货地址不存在"})
        # 订单id 年月日+user.id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 总数目
        total_count = 0
        # 总价格
        total_price = 0
        transit_price = 10

        # 事务保存点
        save_id = transaction.savepoint()
        try:
            # 向数据表df_order_info中添加记录
            order = OrderInfo.objects.create(order_id=order_id, user=user, addr=addr, pay_method=pay_method,
                                             total_count=total_count, total_price=total_price,
                                             transit_price=transit_price)
            # 向数据表df_order_goods中添加记录
            sku_ids = sku_ids.split(",")
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            for sku_id in sku_ids:
                try:
                    # 加锁 悲观锁 一个用户先拿到锁后另一个用户堵塞，等锁释放后另一个用户拿到锁继续执行，
                    # 用于解决并发问题 相当于 select * from df_goods_sku where id=sku_id for update;
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # 事务回滚至保存点
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errorMsg': "商品不存在"})
                count = conn.hget(cart_key, sku_id)
                # 判断库存
                if int(count) > sku.stock:
                    # 事务回滚至保存点
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 5, 'errorMsg': "库存不足"})
                OrderGoods.objects.create(order=order, sku=sku, count=count, price=sku.price)
                # 更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # 累加计算订单商品的总价格，总数量
                amount = sku.price * int(count)
                total_count += int(count)
                total_price += amount
            # 更新订单信息表中的总数量，总价格
            order.total_price = total_price
            order.total_count = total_count
            order.save()
        except Exception as result:
            # 事务回滚至保存点
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errorMsg': "创建订单失败"})
        # 提交事务
        transaction.savepoint_commit(save_id)
        # 清除购物车中记录
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 6, 'errorMsg': "创建订单成功"})


class OrderPayView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errorMsg': '请登录账号'})
        # 接收参数
        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 1, 'errorMsg': "订单号有误"})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errorMsg': "订单不存在"})

        # 支付接口初始化
        alipay = AliPay(
            appid="2016101700706390",
            app_notify_url=None,
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            sign_type="RSA2",
            debug=True  # 默认False，表示真实地址，设为True代表沙箱地址
        )
        total_pay = order.total_price + order.transit_price
        # 调用支付接口
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject="天天生鲜支付%s" % order.order_id,
            return_url=None,
            notify_url=None
        )
        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class OrderCheckView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errorMsg': '请登录账号'})
        # 接收参数
        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 1, 'errorMsg': "订单号有误"})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errorMsg': "订单不存在"})

        # 支付接口初始化
        alipay = AliPay(
            appid="2016101700706390",
            app_notify_url=None,
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            sign_type="RSA2",
            debug=True  # 默认False，表示真实地址，设为True代表沙箱地址
        )
        # 调用查询支付结果的接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            code = response.get('code')
            trade_status = response.get('trade_status')

            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 支付成功
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                return JsonResponse({'res': 3, 'errorMsg': "支付成功"})
            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                time.sleep(3)
                continue
            else:
                return JsonResponse({'res': 3, 'errorMsg': "支付失败"})


class OrderCommentView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        user = request.user
        if not order_id:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, order_status=4)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount = order_sku.count * order_sku.price
            order_sku.amount = amount
        order.order_skus = order_skus
        return render(request, 'order_comment.html', {'order': order})

    def post(self, request, order_id):
        user = request.user
        if not order_id:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, order_status=4)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order', kwargs={'page': 1}))
        # 获取评论条数
        total_count = request.POST.get('total_count')
        total_count = int(total_count)
        for i in (1, total_count+1):
            #  获取评论的商品的Id
            sku_id = request.POST.get('sku_%d' % i)
            #  获取评论内容
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5
        order.save()
        return redirect(reverse('user:order', kwargs={'page': 1}))
