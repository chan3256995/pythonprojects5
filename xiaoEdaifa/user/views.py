import traceback
import re
import logging
import logging
from user import user_utils
logger = logging.getLogger('stu')
from utils import mcommon
from rest_framework.views import APIView
from user import models
import traceback
from utils.String import REGEX_MOBILE
from trade import models as trade_models
from trade import models as trade_models
from rest_framework.pagination import PageNumberPagination
from utils import m_serializers
from utils import permission
import  utils.m_serializers
from utils.m_serializers import TradeAddOrdersSerializer,UserRegisterSerializer,UserQuerySerializer,UserUpdateSerializer
from django.http.response import JsonResponse,HttpResponse
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from django.db import transaction
from rest_framework.mixins import CreateModelMixin,RetrieveModelMixin,UpdateModelMixin,ListModelMixin,DestroyModelMixin
from rest_framework.viewsets import GenericViewSet
from utils import encryptions
import time
import json
from trade import models as trmodels
from django.db.models import Q
from user import trade_views
from trade import trade_utils
from utils import commom_utils
from xiaoEdaifa import settings
from utils import mglobal

def md5(user):
    import  hashlib
    import time
    ctime  = str(time.time())
    m = hashlib.md5(bytes(user,encoding='utf-8'))
    m.update(bytes(ctime,encoding='utf-8'))
    return m.hexdigest()


from utils.auth import Authtication
# 用户登录


class LoginView(APIView):
    authentication_classes = []

    def post(self,request, *args, **kwargs):

        print(request.data)
        ret = {'code': "1000", 'message': ""}
        try:
            # raise Exception
            name = request.data.get('username')
            print(name)
            pwd = request.data.get('password')
            print(pwd)
            pwd = encryptions.get_sha_encryptions(pwd)
            print(pwd)
            user_obj = models.User.objects.filter(user_name=name, password=pwd).first()
            if not user_obj:
                ret['code'] = "1001"
                ret['message'] = '用户名或密码错误'
            else:
                token = commom_utils.md5(name)
                models.UserToken.objects.update_or_create(user=user_obj, defaults={'token': token,'add_time':time.time()})
                user_ser = m_serializers.UserQuerySerializer(instance=user_obj, many=False)
                ret['code'] = "1000"
                ret['message'] = '登录成功'
                ret['token'] = token
                ret['user'] = user_ser.data
        except:
            traceback.print_exc()
            logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            ret['code'] = "1001"
            ret['message'] = '登录失败'
            pass
        return JsonResponse(ret)


class UserMulOrderSaveViewSet(CreateModelMixin,GenericViewSet):
    """
     多个一起提交保存
    """
    serializer_class = m_serializers.TradeAddOrdersSerializer

    class TemOrderGoodsSer(serializers.ModelSerializer):
        """
        临时验证字段的类
        """
        class Meta:
            model = trmodels.OrderGoods
            fields = ("shop_floor", "shop_stalls_no","art_no","shop_market_name",
                      "goods_color",
                      "goods_count",
                      "goods_price")
            # 查表深度  关联表的数据也会查处出来  深度值官方推荐 0-10
            depth = 0

    # 生成订单号函数
    def generate_order_sn(self):
        # 当前时间+userid+随机数
        from time import strftime
        from random import Random
        random_ins = Random()
        order_sn = "os{time_str}{userid}{ranstr}".format(time_str=strftime("%Y%m%d%H%M%S"),
                                                       userid=self.request.user.id,
                                                       ranstr=random_ins.randint(10, 99999))
        print(order_sn)
        return order_sn

    def create(self, request, *args, **kwargs):
        data_list = request.data.get("order_list")
        data_list = json.loads(data_list)
        ret = {"code":"1000", "message":""}
        try:
            # 先对数据进行一次全面检测-------------------------------------------------
            for item in data_list:
                self.serializer_class = m_serializers.TradeAddOrdersSerializer
                # 得请求数据然后得到序列化对象  得到的是上面serializer_class对象模型
                serializer = self.get_serializer(data=item)
                # serializer = TradeOrderSerializer(data=item)
                # 进行数据校验
                serializer.is_valid(raise_exception=True)
                orderGoodsList = item['orderGoods']
                for orderGoods in orderGoodsList:
                    self.serializer_class = self.TemOrderGoodsSer
                    ser = self.get_serializer(data=orderGoods)
                    ser.is_valid(raise_exception=True)
            # 先对数据进行一次全面检测-------------------------------------------------
        except:
            traceback.print_exc()
            ret['code']="1001"
            ret['message'] = serializer.errors
            logger.info('%s url:%s method:%s' % ( traceback.format_exc(),request.path, request.method))

            return Response(ret)

        try:
            with transaction.atomic():
                for item in data_list:
                    self.serializer_class = m_serializers.TradeAddOrdersSerializer
                    # 得请求数据然后得到序列化对象  得到的是上面serializer_class对象模型
                    serializer = self.get_serializer(data=item)

                    # 进行数据校验
                    serializer.is_valid(raise_exception=True)
                    serializer.validated_data['order_number'] = self.generate_order_sn()
                    serializer.validated_data['add_time'] = time.time()*1000
                    print("添加时间-----")
                    order = self.perform_create(serializer)
                    orderGoodsList = item['orderGoods']
                    order_agency_fee = 0  # 代拿费用
                    logisitcs_name = item.get('logistics_name')
                    # 请求的质检服务
                    req_quality_testing_name = item.get('quality_testing_name')
                    # 默认 无质检
                    quality_testing_fee = 0.0
                    quality_testing_name = "基础质检"
                    logistics = trade_models.Logistics.objects.filter(logistics_name = logisitcs_name).first()


                    logistics_fee = logistics.logistics_price
                    # 订单里的商品总数量
                    order_goods_counts = 0

                    # 商品总费用
                    order_goods_fee = 0.0
                    for orderGoods in orderGoodsList:
                        # raise DatabaseError  # 报出错误，检测事务是否能捕捉错误
                        goods_count = float(orderGoods.get('goods_count'))
                        goods_price = float(orderGoods.get('goods_price'))
                        order_goods_counts = order_goods_counts+goods_count
                        order_agency_fee = order_agency_fee*1.0 + goods_count * utils.String.AGENCY_FEE*1.0
                        order_goods_fee = order_goods_fee + goods_price * goods_count *1.0
                        self.serializer_class = m_serializers.TradeOrderGoodsSerializer
                        orderGoods['order'] = order.id
                        ser = self.get_serializer(data=orderGoods)
                        ser.is_valid(raise_exception=True)
                        ser.save()
                    if order_goods_counts > 2:
                        logistics_fee = logistics.logistics_price + 5

                    if req_quality_testing_name is not None and req_quality_testing_name!= "":
                        quality_test_query = trade_models.QualityTest.objects.filter(quality_testing_name = req_quality_testing_name).first()
                        # 质检服务费
                        if quality_test_query is not None:
                            quality_testing_name = quality_test_query.quality_testing_name
                            quality_testing_fee = quality_test_query.quality_testing_price * order_goods_counts

                    order.quality_testing_name = quality_testing_name
                    order.quality_testing_fee = quality_testing_fee
                    order.logistics_fee = logistics_fee
                    order.agency_fee = order_agency_fee
                    total_fee = order_goods_fee + logistics_fee + order_agency_fee + quality_testing_fee
                    order.total_price = total_fee
                    order.save()

        except:
            traceback.print_exc()
            ret['code']="1001"
            ret['message'] = "保存数据失败"
            return Response(ret)
        headers = self.get_success_headers(serializer.data)
        return Response(ret, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        return serializer.save()


class NahuoUserOrderGoodsAlterView(APIView):
    # 拿货人修改订单状态
    permission_classes = [permission.NahuoUserpermission, ]
    # status_choices = (
    # (1, '待付款'),
    # (2, '已付款'),
    # (3, '拿货中'),
    # (4, '已拿货'),
    # (5, '已发货'),
    # (6, '已退款'),
    # (7, '明日有货'),
    # )
    status_choices = mcommon.status_choices

    def post(self, request, *args, **kwargs):
        ret = {"code":"1000","message": ""}
        # 3拿货中 4 已经拿货  5已发货 7,明日有货 , 9其他状态
        # 接受拿货人usertype = 2 修改的值
        acp_status = [mcommon.status_choices2.get("拿货中"),
                      mcommon.status_choices2.get("已拿货"),
                      mcommon.status_choices2.get("已发货"),
                      mcommon.status_choices2.get("明日有货"),
                      mcommon.status_choices2.get("其他状态"),
                      ]
        data = self.request.data
        # data['status'] 拿货人 usertype=2 的用户 请求要修改状态值
        if data['status'] not in acp_status:
            ret['code'] = 1001;
            ret['message'] = "status错误"
            return Response(ret)

        query = trade_models.OrderGoods.objects.filter(id=data['order_goods_id'])
        if query.count() == 1:
            # 接受修改的状态
            acp_status = []
            order_goods = query.first()
            if order_goods.status == mcommon.status_choices2.get("拿货中"):
                # 拿货中状态只能修改为 4已拿货 和 5已发货 和 7明日有货 9其他状态
                acp_status = [mcommon.status_choices2.get("已拿货"),
                              mcommon.status_choices2.get("已发货"),
                              mcommon.status_choices2.get("明日有货"),
                              mcommon.status_choices2.get("其他状态"),
                              ]
            elif order_goods.status == mcommon.status_choices2.get("已拿货"):
                # 已拿货状态只能修 和 已发货
                acp_status = [mcommon.status_choices2.get("已发货")]
            if data['status'] not in acp_status:
                ret['code'] = "1001";
                ret['message'] = "status错误"
                return Response(ret)
            try:
                query.update(status=data['status'])
                ret['code'] = "1000"
                ret['message'] = "更新成功"
                return Response(ret)
            except:
                ret['code'] = "1001";
                ret['message'] = "更新数据库失败"
                return Response(ret)
        else:
            ret['code'] = "1001"
            ret['message'] = "数据错误"
            return Response(ret)


class OrderGoodsViewSet(RetrieveModelMixin,GenericViewSet):
    serializer_class = m_serializers.OrderGoodsSerializer
    queryset =  trade_models.OrderGoods.objects.all()

    def retrieve(self, request, *args, **kwargs):
        print(kwargs.get("pk"))
        orderGoods = trade_models.OrderGoods.objects.filter(id = kwargs.get("pk")).first()
        serializer = self.get_serializer(orderGoods)
        return Response(serializer.data)
    # def get(self, request, *args, **kwargs):
    #     print(request.data)
    #     id = request._request.GET.get("id")
    #     orderGoods = trade_models.OrderGoods.objects.filter(id=id)
    #     ser = m_serializers.OrderGoodsSerializer(instance=orderGoods, many=True)
    #     # order = orderGoods.order
    #     # if request.user == order.order_owner:
    #     #     ser =  m_serializers.OrderGoodsSerializer(instance = orderGoods,many = True)
    #     return Response(ser.data)


class UserOrderGoodsChangeViewSet(APIView):
        # serializer_class = m_serializers.TradeOrderGoodsRefundSerializer
        # 订单状态选择
        status_choices = mcommon.status_choices
        # status_choices = (
        #     (1, '待付款'),
        #     (2, '已付款'),
        #     (3, '拿货中'),
        #     (4, '已拿货'),
        #     (5, '已发货'),
        #     (6, '已退款'),
        #     (7, '明日有货'),
        # )
        def post(self,request,*args,**kwargs):
            ret = {"code":"1000","message":""}
            data = self.request.data
            if data['status'] == mcommon.status_choices2.get('已付款'):
                # 任何人都无法修改为已付款状态
                return Response({"message":"访问拒绝"})
            elif data['status'] == mcommon.status_choices2.get('拿货中'): # data['status'] 访问要修改的状态
                if self.request.user.type == 2:
                    query = trade_models.OrderGoods.objects.filter(id=data['order_goods_id'])
                    order_goods = query.first()
                    if order_goods is not None and (order_goods.status == mcommon.status_choices2.get('已付款')):
                        query.update(status=mcommon.status_choices2.get('拿货中'))
                        ret["message"] = "更新成功"
                        return Response(ret)
                    else:
                        ret["code"] = "1001"
                        ret["message"] = "更新失败"
                        return Response(ret)

            elif data['status'] == mcommon.status_choices2.get('已拿货') :
                # 用户类型2 才有权修改该状态
                if self.request.user.type == 2:
                    query = trade_models.OrderGoods.objects.filter(id = data['order_goods_id'])
                    order_goods = query.first()
                    if order_goods is not None and (order_goods.status == mcommon.status_choices2.get('拿货中') or
                                                    order_goods.status == mcommon.status_choices2.get('已付款')):
                        query.update(status = mcommon.status_choices2.get('已拿货'))
                        ret["message"] = "更新成功"
                        return Response(ret)
                    else:
                        ret["code"] = "1001"
                        ret["message"] = "更新失败"
                        return Response(ret)
            elif data['status'] == mcommon.status_choices2.get('已发货') :
                # 用户类型2 才有权修改该状态
                if self.request.user.type == 2:
                    query = trade_models.OrderGoods.objects.filter(id = data['order_goods_id'])
                    order_goods = query.first()
                    if order_goods is not None and (order_goods.status == mcommon.status_choices2.get('已付款') or
                                                    order_goods.status == mcommon.status_choices2.get('拿货中') or
                                                    order_goods.status == mcommon.status_choices2.get('已拿货')):
                        query.update(status = mcommon.status_choices2.get('已发货'))
                        ret["message"] = "更新成功"
                        return Response(ret)
                    else:
                        ret["code"] = "1001"
                        ret["message"] = "更新失败"
                        return Response(ret)
            return Response(ret)



class UsersPagination(PageNumberPagination):
    # 指定每一页的个数
    page_size = 10
    # 可以让前端来设置page_szie参数来指定每页个数
    page_size_query_param = 'page_size'
    # 设置页码的参数
    page_query_param = 'page'


class UserOrderViewSet(ListModelMixin,DestroyModelMixin, GenericViewSet):
        # authentication_classes = []
        serializer_class = m_serializers.TradeOrderQuerySerializer
        # 设置分页的class
        pagination_class = UsersPagination
        # def create(self, request, *args, **kwargs):
        #     # 得请求数据然后得到序列化对象  得到的是上面serializer_class对象模型
        #     serializer = self.get_serializer(data=request.data)
        #     # 进行数据校验
        #     serializer.is_valid(raise_exception=True)
        #     order = self.perform_create(serializer)
        #     ret_dict = serializer.data
        #     headers = self.get_success_headers(serializer.data)
        #     return Response(ret_dict, status=status.HTTP_201_CREATED, headers=headers)

        def list(self, request, *args, **kwargs):
            print(request.data)
            print("333333333333333333333333333")
            # trade_models.OrderGoods.filter()
            ret = {"code": "1000", "message": ""}
            try:
                queryset = self.filter_queryset(self.get_queryset())

                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    return self.get_paginated_response(serializer.data)

                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)
            except:
                traceback.print_exc()
                logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
                ret['code'] = "1001"
                ret['message'] = " 查询异常"
                return Response(ret)

        def destroy(self, request, *args, **kwargs):

            ret = {"code": "1000", "message": ""}
            try:
                order_number = kwargs.get("pk")
                order = trade_models.Order.objects.filter(order_number=order_number).first()
                if order.order_owner != request.user:
                    #
                    ret['code'] = "1001"
                    ret['message'] = "删除失败！非法订单"
                    return Response(ret)
                else:
                    order_goods_query = trade_models.OrderGoods.objects.filter(order=order)
                    for order_goods in order_goods_query:
                        if order_goods.status != mcommon.status_choices2.get("待付款"):
                            ret['code'] = "1001"
                            ret['message'] = "只能删除未付款订单"
                            return Response(ret)

                    order.delete()
            except:
                traceback.print_exc()
                logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
                ret['code'] = "1001"
                ret['message'] = "删除异常"
                return Response(ret)

            print("pk",kwargs.get("pk"))
            print("order destroy")
            ret['code'] = "1000"
            ret['message'] = "删除成功！"
            return Response(ret)

        def get_queryset(self):
            try:
                print(self.request.query_params)
                query_keys = self.request.query_params.get("q")
                status_filter = self.request.query_params.get("status")
                refund_apply_status = self.request.query_params.get("refund_apply_status")


                print("query_keys")
                print(query_keys)
                print(status_filter)
                if query_keys is not None:
                    args = Q(order_number=query_keys) | Q(consignee_name=query_keys) | Q(logistics_number=query_keys)
                    # 手机字段为数字 用字符查询会报错
                    if query_keys.isdigit():
                        args = args | Q(consignee_phone=query_keys)
                    return trade_models.Order.objects.filter(Q(order_owner=self.request.user) & args).order_by('-add_time')
                elif status_filter is not None:
                    qy =  trade_models.Order.objects.filter(order_owner=self.request.user,orderGoods__status = status_filter).distinct().order_by("-add_time")
                    print("9999999999")
                    print(len(qy))
                    return qy
                elif refund_apply_status is not None :
                    if refund_apply_status == "有售后订单":
                        qy =trade_models.Order.objects.filter(Q(order_owner=self.request.user) & (Q(orderGoods__refund_apply_status = mcommon.refund_apply_choices2.get("拦截发货"))
                                                                                                  | Q(orderGoods__refund_apply_status = mcommon.refund_apply_choices2.get("退货退款"))
                                                                                                  | Q(orderGoods__refund_apply_status = mcommon.refund_apply_choices2.get("仅退款"))
                                                                                                  )).distinct().order_by('-add_time')
                        return qy
                else:
                    return trade_models.Order.objects.filter(order_owner=self.request.user).order_by('-add_time')
            except:
                traceback.print_exc()


        def get_serializer_class(self):
            if self.action == "retrieve":
                return m_serializers.TradeOrderQuerySerializer
            elif self.action == "create":
                return m_serializers.TradeOrderQuerySerializer
            elif self.action == "update":
                return m_serializers.TradeOrderQuerySerializer
            elif self.action == "delete":
                return m_serializers.TradeOrderQuerySerializer

            return m_serializers.TradeOrderQuerySerializer

        def get_object(self):
            return self.request.user


# 用户拦截发货
class UserStopDeliverView(APIView):
    # 商品状态为拿货中，已拿货，可以进行拦截发货
    def post(self,request, *args, **kwargs):
        try:
            with transaction.atomic():
                ret = {"code": "1000", "message": ""}
                print("拦截发货......")
                print(request.data)
                req_data = request.data
                order_goods_number = req_data.get("goods_number")
                order_goods = trade_models.OrderGoods.objects.filter(goods_number = order_goods_number).first()
                # 不是该用户商品不能请求
                if order_goods is None or request.user != order_goods.order.order_owner:
                    ret['code'] = "1001"
                    ret['message'] = '无效参数'
                    return JsonResponse(ret)
                order_goods_status = order_goods.status
                if order_goods_status == mcommon.status_choices2.get("拿货中") or order_goods_status == mcommon.status_choices2.get("已拿货"):
                    order_goods.is_stop_deliver = True
                    order_goods.log = "拦截发货--"+mcommon.format_from_time_stamp(time.time()) + "\n"
                    is_ok = user_utils.check_pay_password(self, self.request.user, req_data.get("pay_pwd"))
                    if is_ok is True:
                        trade_money = mcommon.service_fee * order_goods.goods_count
                        data = {
                            "user": request.user,
                            "trade_number": trade_utils.get_trade_number(request.user),
                            "trade_source": mcommon.trade_source_choices2.get("其他费用"),
                            "cash_in_out_type": mcommon.cash_in_out_type_choices2.get("支出"),
                            "user_balance": request.user.balance,
                            "add_time": time.time() * 1000,
                            "trade_money": trade_money,
                            "is_pass": True,
                            "message": "拦截发货费用，订单编号：" + order_goods.order.order_number + " 商品编号：" + order_goods.goods_number,
                        }

                        if request.user.balance<trade_money:
                            ret['code'] = "1001"
                            ret['message'] = "余额不足"
                            return Response(ret)
                        order_goods.save()
                        request.user.balance = request.user.balance - trade_money
                        data['user_balance'] = request.user.balance
                        trade_info = trade_models.TradeInfo.objects.create(**data)
                        request.user.save()
                    else:
                        ret['code'] = "1001"
                        ret['message'] = "支付密码错误"
                        return Response(ret)

        except:
            ret['code'] = "1001"
            ret['message'] = '查询异常'
            traceback.print_exc()
            logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            return JsonResponse(ret)
        return JsonResponse(ret)


# 重置密码
class ResetPasswordView(APIView):
    # authentication_classes = []
    def post(self,request, *args, **kwargs):
        try:
            ret = {"code":"1000","message":""}
            data = request.data
            pwd = data.get("password")
            # 判断非游客用户
            if pwd is not None and isinstance(request.user,models.User) :
                with transaction.atomic():
                    print( request.user.password)
                    e_pwd =  encryptions.get_sha_encryptions(pwd)
                    token = commom_utils.md5(request.user.user_name)
                    request.user.password = e_pwd
                    request.user.save()
                    models.UserToken.objects.update_or_create(user=request.user,defaults={'token': token, 'add_time': time.time()})

            else:
                ret['code'] = "1001"
                ret['message'] = '无效参数'

                return JsonResponse(ret)
        except:

            ret['code'] = "1001"
            ret['message'] = '查询异常'
            traceback.print_exc()
            return JsonResponse(ret)

        return JsonResponse(ret)


# 忘记密码
class ForgetPasswordView(APIView):

    # 注册时候检查一个一个异步检查是否存在
    authentication_classes = []

    def post(self,request, *args, **kwargs):
        try:
            ret = {"code":"1000","message":""}
            data = request.data
            email = data.get("email")
            if email is not None  :
                user =models.User.objects.filter(email=email).first()
                if user is not None:
                    token = commom_utils.md5(user.user_name)
                    models.UserToken.objects.update_or_create(user=user,defaults={'token': token, 'add_time': time.time()})
                    # VUE_BASE_URL
                    mcommon.send_email(subject= " 17代拿网找回密码",sender=settings.EMAIL_FROM,message="找回密码",html_message=mglobal.STATIC_VUE_URL+"/#/pc/resetPassword/?access_token="+token, receiver=[email])
            else:
                ret['code'] = "1001"
                ret['message'] = '无效参数'

                return JsonResponse(ret)
        except:

            ret['code'] = "1001"
            ret['message'] = '查询异常'
            traceback.print_exc()
            return JsonResponse(ret)

        return JsonResponse(ret)

class UserCheckView(APIView):
    # 注册时候检查一个一个异步检查是否存在
    authentication_classes = []

    def post(self,request, *args, **kwargs):
        ret = {"code":"1000","message":""}
        data = request.data
        username = data.get("username")
        email = data.get("email")
        phone = data.get("phone")
        qq = data.get("qq")
        print(data)

        if username is None and email is None and phone is None and qq is None:
            ret['code'] = "1001"
            ret['message'] = '无效参数'
            return JsonResponse(ret)
        if username is not None :
            user_obj = models.User.objects.filter(user_name=username).first()
            if user_obj is not None:
                ret['code'] = "1002"
                ret['message'] = username + ' 已经存在'
        elif email is not None:
            user_obj = models.User.objects.filter(email=email).first()
            if user_obj is not None:
                ret['code'] = "1002"
                ret['message'] = email + ' 已经存在'
        elif phone is not None:
            # 验证手机号码是否合法
            if not re.match(REGEX_MOBILE, phone):
                ret['code'] = "1001"
                ret['message'] = '无效参数'
                return JsonResponse(ret)
            user_obj = models.User.objects.filter(phone=phone).first()
            if user_obj is not None:
                ret['code'] = "1002"
                ret['message'] = phone + ' 已经存在'
        elif qq is not None:
            user_obj = models.User.objects.filter(qq=qq).first()
            if user_obj is not None:
                ret['code'] = "1002"
                ret['message'] = qq + ' 已经存在'

        return JsonResponse(ret)


class UserViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    def update(self, request, *args, **kwargs):
        try:
            print(request.data)
            ret = {"code": "1000", "message": ""}
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

        except:
            traceback.print_exc()
            logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            ret['code'] = "1001"
            ret['message'] = "修改异常"
            return JsonResponse(ret)
        return JsonResponse(ret)

    def retrieve(self, request, *args, **kwargs):
        try:
            user_id = kwargs.get("pk")
            print(user_id)
            ret = {"code": "1000", "message": ""}
            user_ser = UserQuerySerializer(request.user, many=False)
            ret['user'] = user_ser.data
            return JsonResponse(ret)
        except:
            traceback.print_exc()
            logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            ret['code'] = "1001"
            ret['message'] = "获取信息异常"
            return JsonResponse(ret)


    # queryset = models.User.objects.all()
    # self.action 必须要继承了 ViewSetMixin 才有此功能
    # get_serializer_class 的源码位置在 GenericAPIView 中
    def get_serializer_class(self):
        print("-----action------{}".format(self.action))
        if self.action == "retrieve":
            print('-UserViewSet--------retrieve-------------')
            return UserQuerySerializer
        elif self.action == 'update':
            print('-UserViewSet--------update-------------')
            return UserUpdateSerializer

        print("---------UserViewSet---------")
        return UserUpdateSerializer

    # 重写父类 CreateModelMixin 方法perform_create
    def perform_create(self, serializer):
        return serializer.save()

    # 重写父类 GenericViewSet 的get_object   RetrieveModelMixin 调用子类的get_object
    # 因为要涉及到 个人中心的操作需要传递过去 用户的 id, 重写 get_object 来实现
    def get_object(self):
        return self.request.user


class UserRefundApplyViewSet(CreateModelMixin, DestroyModelMixin, GenericViewSet):
    class TemSerializer(serializers.ModelSerializer):
        class Meta:
            model = trade_models.RefundApply
            fields = ("orderGoods", "refund_apply_type")
            depth = 0
    serializer_class = m_serializers.UserOrderGoodsRefundApplySerializer

    def destroy(self, request, *args, **kwargs):
        # 传入的pk 为orderGoods id 即取消该orderGooods申请退款
        ret = {"code": "1000", "message": ""}
        order_goods_id = kwargs.get("pk")
        # 根据请求的 商品id 的到数据库商品对象  拿到数据是为了检验是否为请求者自己的商品
        orderGoods = trade_models.OrderGoods.objects.filter(id=order_goods_id).first()
        if orderGoods.order.order_owner == request.user:
            try:
                with transaction.atomic():
                    refund_apply_query = trade_models.RefundApply.objects.filter(orderGoods=order_goods_id)
                    refund_apply_object = refund_apply_query.first()
                    apply_goods_counts = refund_apply_object.goods_counts
                    # 退回服务费
                    return_server_fee = mcommon.service_fee * apply_goods_counts
                    is_suc = self.return_server_fee( self.request.user, orderGoods, orderGoods.order, return_server_fee)
                    if is_suc is False:
                        raise Exception
                    trade_models.OrderGoods.objects.filter(id =order_goods_id).update(refund_apply_status = 0)
                    refund_apply_query.delete()
            except:
                ret['code'] = "1001"
                ret['message'] = "撤销失败"
                traceback.print_exc()
                logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
                return Response(ret)
        else:
            ret['code'] = "1001"
            ret['message'] = "撤销失败"
            logger.info('%s url:%s method:%s' % ("请求商品不是该用户", request.path, request.method))
            return Response(ret)
        return  Response(ret)

    def create(self, request, *args, **kwargs):
        ret = {"code":"1000","message":""}
        req_data = request.data
        goods_number = req_data.get("goods_number")
        orderGoods = trade_models.OrderGoods.objects.filter(goods_number=goods_number).first()
        # 商品当前状态
        goods_cur_status = orderGoods.status
        # 用户申请退款的类型 refund_apply_type
        refund_apply_type = int(req_data.get("refund_apply_type"))
        # 找到商品归属的订单
        order = orderGoods.order
        if request.user != order.order_owner:
                ret['code'] = "1001"
                ret['message'] = '申请失败'
                traceback.print_exc()
                logger.info('userid->%s ,  url:%s method:%s' % (request.user.id, request.path, request.method))

                logger.info(
                    'userid->%s 申请的订单不是该用户的订单 不可修改,  url:%s method:%s' % (request.user.id, request.path, request.method))
                print("申请的订单不是该用户的订单 不可修改")
                ret['code'] = "1001"
                ret['message'] = "非法数据"
                return Response(ret)

        refund_apply_obj = trade_models.RefundApply.objects.filter(orderGoods=orderGoods).first()
        if refund_apply_obj is not None:
            #  有申请未处理
            ret['code'] = "1001"
            ret['message'] = "申请失败，有未处理申请"
            print("申请失败，有未处理申请")
            return Response(ret)

        try:
            if refund_apply_type == mcommon.refund_apply_choices2.get("取消订单"):
                if orderGoods.status != mcommon.status_choices2.get('待付款'):
                    ret['code'] = "1001"
                    ret['message'] = "该状态不允许取消订单"
                    print("该状态不允许取消订单")
                    return Response(ret)
                is_suc = self.cancel_order_operate(goods_number)
                if is_suc:
                    ret['code'] = "1000"
                    ret['message'] = "取消成功"
                else:
                    ret['code'] = "1000"
                    ret['message'] = "取消失败"
                return Response(ret)

            # 1 申请退货退款
            if refund_apply_type == mcommon.refund_apply_choices2.get("退货退款"):
                # 有操作异常所有都回滚
                with transaction.atomic():
                    # 支持退货退款的状态有 5已发货
                    if orderGoods.status != mcommon.status_choices2.get("已发货"):
                        ret['code'] = "1001"
                        ret['message'] = "该状态不允许申请"
                        print("该状态不允许申请")
                        return Response(ret)
                    else:
                        is_ok = user_utils.check_pay_password(self,self.request.user,req_data.get("pay_pwd"))
                        if is_ok is False:
                            ret['code'] = "1001"
                            ret['message'] = "支付密码错误"
                            return Response(ret)
                        req_data["orderGoods"] = orderGoods.id
                        suc = self.apply_goods_operate(req_data, goods_number, refund_apply_type)
                        if suc:
                            req_goods_counts = float(req_data.get("goods_counts"))
                            server_fee = mcommon.service_fee * req_goods_counts
                            if self.request.user.balance < server_fee:
                                ret['code'] = "1001"
                                ret['message'] = "余额不足"
                                return Response(ret)

                            is_ret_suc = self.pay_server_fee(self.request.user, orderGoods, order, server_fee)
                            if is_ret_suc:
                                ret['code'] = "1000"
                                ret['message'] = "退货退款申请成功"
                            else:
                                ret['code'] = "1001"
                                ret['message'] = "申请退货退款失败"
                            return Response(ret)
                        else:
                            ret['code'] = "1001"
                            ret['message'] = "申请退货退款失败"
                            return Response(ret)

            if refund_apply_type == mcommon.refund_apply_choices2.get("仅退款"):  # 2 申请仅退款
                # 支持仅退款的状态只有  2已付款 跟 7明日有货 9其他状态
                if orderGoods.status != mcommon.status_choices2.get('已付款') \
                        and orderGoods.status != mcommon.status_choices2.get('明日有货')\
                        and orderGoods.status != mcommon.status_choices2.get('其他状态'):
                    ret['code'] = "1001"
                    ret['message'] = "该状态不允许申请仅退款"
                    print("该状态不允许申请仅退款")
                    return Response(ret)
                else:
                    suc = self.return_moneys_only_operate(req_data, orderGoods, order)
                    if suc:
                        ret['code'] = "1000"
                        ret['message'] = "退款成功"
                        return Response(ret)
                    else:
                        ret['code'] = "1001"
                        ret['message'] = "退款失败"
                        return Response(ret)

            if refund_apply_type == mcommon.refund_apply_choices2.get("拦截发货"):
                with transaction.atomic():
                    if orderGoods.status == mcommon.status_choices2.get("拿货中") or orderGoods.status == mcommon.status_choices2.get("已拿货") and  orderGoods.refund_apply_status == mcommon.refund_apply_choices2.get("无售后"):
                        trade_money = mcommon.service_fee * orderGoods.goods_count
                        data = {
                            "user": request.user,
                            "trade_number": trade_utils.get_trade_number(request.user),
                            "trade_source": mcommon.trade_source_choices2.get("其他费用"),
                            "cash_in_out_type": mcommon.cash_in_out_type_choices2.get("支出"),
                            "user_balance": request.user.balance,
                            "add_time": time.time() * 1000,
                            "trade_money": trade_money,
                            "is_pass": True,
                            "message": "拦截发货费用，订单编号：" + orderGoods.order.order_number + " 商品编号：" + orderGoods.goods_number,
                        }
                        req_data['apply_message'] = "拦截发货"
                        req_data['return_logistics_name'] = "无"
                        req_data['return_logistics_number'] = "无"
                        req_data['goods_counts'] = orderGoods.goods_count
                        is_ok = user_utils.check_pay_password(self, self.request.user, req_data.get("pay_pwd"))
                        if is_ok is False:
                            ret['code'] = "1001"
                            ret['message'] = "支付密码错误"
                            return Response(ret)
                        req_data["orderGoods"] = orderGoods.id
                        suc = self.apply_goods_operate(req_data, goods_number, refund_apply_type)
                        if suc:
                            if request.user.balance < trade_money:
                                ret['code'] = "1001"
                                ret['message'] = "余额不足"
                                return Response(ret)

                            request.user.balance = request.user.balance - trade_money
                            data['user_balance'] = request.user.balance
                            trade_info = trade_models.TradeInfo.objects.create(**data)
                            request.user.save()
                        return Response(ret)
                    else:
                        ret['code'] = "1001"
                        ret['message'] = "状态异常"
                        return Response(ret)
        except:
            traceback.print_exc()
            logger.info('%s  数据格式错误 url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            ret['code'] = "1001"
            ret['message'] = "异常"
            return Response(ret)

    # 服务费退回
    def return_server_fee(self, user, order_goods, order, other_fee):
        try:
            other_fee = float(other_fee)
        except:
            return False
        if other_fee < 0 or other_fee == 0:
            return False

        data = {
            "user": user,
            "trade_number": trade_utils.get_trade_number(user),
            "trade_source": mcommon.trade_source_choices2.get("其他费用"),
            "cash_in_out_type": mcommon.cash_in_out_type_choices2.get("收入"),
            "user_balance": user.balance,
            "add_time": time.time() * 1000,
            "trade_money": other_fee,
            "is_pass": True,
            "message": "退货服务费 订单编号：" + order.order_number + " 商品编号：" + order_goods.goods_number,

        }
        # with transaction.atomic():
        user.balance = user.balance + other_fee
        data['user_balance'] = user.balance
        trade_info = trade_models.TradeInfo.objects.create(**data)
        user.save()

        return True

    # 支付服务费
    def pay_server_fee(self, user, order_goods, order, other_fee):
        try:
            other_fee =  float(other_fee)
        except:
            return False
        if other_fee < 0 or other_fee == 0 :
            return False
        # 余额不足
        if user.balance < other_fee:
            return False
        data = {
            "user":user,
            "trade_number": trade_utils.get_trade_number(user),
            "trade_source": mcommon.trade_source_choices2.get("其他费用"),
            "cash_in_out_type": mcommon.cash_in_out_type_choices2.get("支出"),
            "user_balance":user.balance,
            "add_time": time.time() * 1000,
            "trade_money": other_fee,
            "is_pass": True,
            "message": "退货服务费 订单编号："+order.order_number+" 商品编号："+order_goods.goods_number,
        }
        # with transaction.atomic():
        user.balance = user.balance - other_fee
        data['user_balance'] = user.balance
        trade_info = trade_models.TradeInfo.objects.create(**data)
        user.save()

        return True

    # 申请 退货退款操作
    def apply_goods_operate(self, req_data, order_goods_number, refund_apply_type):

        self.serializer_class = m_serializers.UserOrderGoodsRefundApplySerializer
        user_goods_refund_apply_serializer = self.get_serializer(data=req_data)
        # 进行数据校验
        user_goods_refund_apply_serializer.is_valid(raise_exception=True)
        # with transaction.atomic():
            # 保存到数据库

        # 更新商品申请退款状态
        order_goods = trade_models.OrderGoods.objects.filter(goods_number=order_goods_number).first()
        # 申请退货商品件数
        apply_goods_counts = req_data.get("goods_counts")
        if apply_goods_counts is not None and str(apply_goods_counts).isdigit():
            if int(apply_goods_counts) > order_goods.goods_count:
                raise Exception
        else:
            raise Exception
        refundApply = self.perform_create(user_goods_refund_apply_serializer)
        order_goods.refund_apply_status = refund_apply_type
        order_goods.save()



        return True

    # 紧退款操作
    def return_moneys_only_operate(self,data,orderGoods,order):
        try:
            # self.serializer_class = self.TemSerializer
            # serializer = self.get_serializer(data=data)
            # # 进行数据校验
            # serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                # 保存到数据库
                # refundApply = self.perform_create(serializer)
                # 更新商品申请退款状态
                orderGoods.refund_apply_status = mcommon.refund_apply_choices2.get("仅退款")
                orderGoods.save()

                orderGoods.status = mcommon.status_choices2.get("已退款")
                orderGoods.refund_apply_status = mcommon.refund_apply_choices2.get("无售后")
                orderGoods.refund_apply_status = 0
                orderGoods.save()

                data = {"trade_money": orderGoods.goods_price + mcommon.service_fee, "add_time": time.time() * 1000}
                ser = m_serializers.OrderGoodsRefundBalanceSerializer(data=data, context={'request': self.request})
                ser.is_valid(raise_exception=True)
                ser.validated_data['trade_number'] = trade_views.BaseTrade(self.request.user).get_trade_number()
                ser.validated_data['trade_source'] = mcommon.trade_source_choices2.get("商品")
                ser.validated_data['cash_in_out_type'] = mcommon.cash_in_out_type_choices2.get("收入")
                ser.validated_data['is_pass'] = True
                # 是否返回其他费用 物流费
                is_return_fee = self.is_return_order_fee(order, orderGoods)
                return_logistics_fee = 0.0
                if is_return_fee:
                    return_logistics_fee = order.logistics_fee

                goods_moneys = orderGoods.goods_price * orderGoods.goods_count
                # 质检服务费
                quality_fee = trade_models.QualityTest.objects.filter(
                    quality_testing_name=order.quality_testing_name).first().quality_testing_price
                trade_moneys = goods_moneys + mcommon.service_fee + return_logistics_fee + quality_fee
                ser.validated_data['trade_money'] = trade_moneys
                money = self.request.user.balance + trade_moneys
                ser.validated_data['message'] = "商品退款，订单编号：" + order.order_number + " 商品编号：" + str(
                    orderGoods.goods_number) + " 商品金额：" + str(goods_moneys) + " 代拿费：" + str(
                    mcommon.service_fee) + "物流费：" + str(return_logistics_fee) + "质检费：" + str(quality_fee)
                ser.validated_data['user_balance'] = money
                ser.validated_data['add_time'] = time.time() * 1000
                self.request.user.balance = money
                self.request.user.save()
                ser.save()

                return True


        except:
            logger.info('%s userid->%s ,  url:%s method:%s' % (
            "申请异常" + traceback.format_exc(), self.request.user.id, self.request.path, self.request.method))
            traceback.print_exc()
            return False


    #取消订单操作
    def cancel_order_operate(self,goods_number):
        try:
            rt = trade_models.OrderGoods.objects.filter(goods_number=goods_number).update(status=mcommon.status_choices2.get("已取消"))

            return True
        except:
            logger.info('%s userid->%s ,  url:%s method:%s' % ("取消订单失败"+traceback.format_exc(), self.request.user.id, self.request.path, self.request.method))
            return False

    def perform_create(self, serializer):
        return serializer.save()

    def get_object(self):
        return self.request.user

    # 是否退 订单其他费用
    def is_return_order_fee(self, order, orderGoods):
        order_goods_queryset = trade_models.OrderGoods.objects.filter(order = order)
        # 只有一个商品 进行退运费
        if len(order_goods_queryset)==1 and order_goods_queryset[0].goods_number == orderGoods.goods_number:
            return True

        for order_goods in order_goods_queryset:
            # 订单内所有商品都是已退款 只剩下最后一个商品 进行退款的时候  其他费才可以退
            if order_goods.status != mcommon.status_choices2.get("已退款") and order_goods.goods_number !=orderGoods.goods_number:
                return False

        return True


class UserRegViewSet(CreateModelMixin, GenericViewSet):
    #  serializer_class  queryset 这两字段继承于GenericViewSet的父类 GenericAPIView
    serializer_class = UserRegisterSerializer
    queryset = models.User.objects.all()
    authentication_classes = []


#   权限分流
    # def get_permissions(self):
    #     if self.action == "retrieve":
    #         return [permission() for permission in self.permission_classes]
    #     elif self.action == "create":
    #         return [permission() for permission in self.permission_classes]
    #     return []

    # 用户注册和 用户详情分为了两个序列化组件
    # self.action 必须要继承了 ViewSetMixin 才有此功能
    # get_serializer_class 的源码位置在 GenericAPIView 中
    def get_serializer_class(self):
        if self.action == "retrieve":

            print('-action--------retrieve-------------')
            return UserQuerySerializer
        elif self.action == "create":
            print('-action--------create-------------')
            return UserRegisterSerializer

    # 重写父类 CreateModelMixin 方法create
    def create(self, request, *args, **kwargs):
        ret = {"code": "1000", "message":""}
        # 得请求数据然后得到序列化对象  得到的是上面serializer_class对象模型
        try:
            request.data['pay_password'] = request.data.get("password")
            serializer = self.get_serializer(data=request.data)
            # 进行数据校验
            serializer.is_valid(raise_exception=True)
        except:
            ret['code'] = "1001"
            ret['message'] =""
            traceback.print_exc()
            logger.debug(traceback.print_exc())
            return Response(ret)

        # 额外给序列化对象添加数据 不能直接给serializer.data添加数据 要通过validated_data这个属性添加  validated_data保存
        # 校验过的字段
        serializer.validated_data['add_time'] = time.time()*1000
        serializer.validated_data['balance'] = 0.0
        serializer.validated_data['type'] = 1


        try:
            # 保存到数据库
            user = self.perform_create(serializer)
        except:
            ret['code'] = "1001"
            ret['message'] = '注册失败'
            traceback.print_exc()
            logger.error(traceback.format_exc())
            return Response(ret)

        ret_dict = serializer.data
        token = md5(ret_dict['user_name'])
        models.UserToken.objects.update_or_create(user=user, defaults={'token': token, 'add_time': time.time()*1000})
        ret['code'] = "1000"
        ret['message'] = '注册成功'
        ret['token'] = models.UserToken.objects.filter(user=user).first().token

        return Response(ret)

    # 重写父类 CreateModelMixin 方法perform_create,要把用户存表里
    def perform_create(self, serializer):
        return serializer.save()


class AlterPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            ret = {"code":"1000","message":""}
            print(request.data)
            new_password = request.data.get("newPassword")
            old_password = request.data.get("oldPassword")
            new_pwd_en = encryptions.get_sha_encryptions(new_password)
            old_pwd_en = encryptions.get_sha_encryptions(old_password)
            if old_pwd_en != request.user.password:
                ret['code'] = "1001"
                ret['message'] = "密码错误"
                return JsonResponse(ret)

            request.user.password = new_pwd_en
            with transaction.atomic():
                request.user.save()
                models.UserToken.objects.update_or_create(user=request.user,defaults={'token': "", 'add_time': time.time() * 1000})
        except:
            traceback.print_exc()
            logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            ret['code'] = "1001"
            ret['message'] = "修改密码失败"
            return JsonResponse(ret)
        return JsonResponse(ret)


class AlterPayPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            ret = {"code":"1000","message":""}
            print(request.data)
            pay_password = request.data.get("payPassword")
            login_password = request.data.get("loginPassword")
            login_pwd_en = encryptions.get_sha_encryptions(login_password)
            pay_pwd_en = encryptions.get_sha_encryptions(pay_password)
            if login_pwd_en != request.user.password:
                ret['code'] = "1001"
                ret['message'] = "登录密码错误"
                return JsonResponse(ret)
            request.user.pay_password = pay_pwd_en
            request.user.save()

        except:
            traceback.print_exc()
            logger.info('%s url:%s method:%s' % (traceback.format_exc(), request.path, request.method))
            ret['code'] = "1001"
            ret['message'] = "修改支付密码失败"
            return JsonResponse(ret)
        return JsonResponse(ret)
