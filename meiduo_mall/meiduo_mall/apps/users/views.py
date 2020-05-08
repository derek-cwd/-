from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render


# Create your views here.
from django.views import View

from meiduo_mall.utils.views import LoginRequiredMixin
from users.models import User, Address
import json, re
from django_redis import get_redis_connection
from celery_tasks.email.tasks import send_verify_email



class UsernameCountView(View):

    def get(self, request, username):


        try:
            count = User.objects.filter(username=username).count()
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg': '访问数据库失败'})

        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'count': count})


class MobileCountView(View):

    def get(self, request, mobile):

        #1.查询mobile在mysql中的个数
        try:
            count = User.object.filter(mobile=mobile).count()
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg': '查询数据库出错'})
        #2. 返回结果(json)
        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'count': count})


class RegisterView(View):

    def post(self, request):
        '''实现注册接口'''

        #1. 接收json参数,获取每一个
        dict = json.loads(request.body.decode())
        username = dict.get('username')
        password = dict.get('password')
        password2 = dict.get('password2')
        mobile = dict.get('mobile')
        allow = dict.get('allow')
        sms_code_client = dict.get('sms_code')

        #2. 整体检验,查看是否有空值
        if not all([username, password, password2, mobile, sms_code_client]):
            return JsonResponse({'code':400,
                                 'errmsg':'缺少必传参数'})
        #3. 单个检验,username是否为5-20位
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return JsonResponse({'code': 400,
                                 'errmsg': 'username不满足格式要求'})
        #4. password是否为8-20位
        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return JsonResponse({'code': 400,
                                 'errmsg': 'pssword不满足格式要求'})
        #5. 判断两个密码是否一致
        if password != password2:
            return JsonResponse({'code': 400,
                                 'errmsg': '两次输入不对'})
        #6. mobile是否为手机格式
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code':400,
                                 'errmsg': '手机号不满足格式要求'})
        #7. allow是否为true
        if allow != True:
            return JsonResponse({'code':400,
                                 'errmsg': 'allow不满足格式要求'})
        #8. 链接redis,获取redis连接对象
        redis_conn = get_redis_connection('verify_code')
        #9. 从redis中,获取保存的短信验证码
        sms_code_server = redis_conn.get('sms_%s' % mobile)

        if not sms_code_server:
            return JsonResponse({'code':400,
                                 'errmsg':'短信验证码过期'})
        #10. 把前后端的短信验证码进行比对
        if sms_code_client != sms_code_server.decode():
            return JsonResponse({'code':400,
                                 'errmsg': '输入的短信验证码不对'})

        #11. 把前端传入的mobile, username, password保存到User
        try:
            user = User.objects.create_user(username=username,
                                     password=password,
                                     mobile=mobile)
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'数据库保存失败'})

        #补充:实现状态保持:
        login(request, user)

        #12. 返回结果(json)
        return JsonResponse({'code': 0,
                             'errmsg': 'ok'})


class LoginView(View):

    def post(self, request):
        '''实现登录功能'''

        #1.接收json参数,获取每一个
        dict = json.loads(request.body.decode())
        username = dict.get('username')
        password = dict.get('password')
        remembered = dict.get('remembered')

        #2.整体检验,查看是否为空
        if not all([username, password]):
            return JsonResponse({'code':400,
                                 'errmsg':'缺少必传参数'})
        #3. username检验
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return JsonResponse({'code': 400,
                                 'errmsg': 'username格式有误'})
        #4. password检验
        if not re.match(r'^[a-zA-Z0-9]{8,20}$', password):
            return JsonResponse({'code': 400,
                                 'errmsg': 'password格式有误'})
        #5. remember 检验是否为布尔值
        if remembered:
            if not isinstance(remembered, bool):
                return JsonResponse({'code': 400,
                                     'errmsg': 'remembered不是bool类型'})
        #6. 登录认证(authenticate),获取用户
        user = authenticate(username=username,
                            password=password)
        #7. 判断用户是否存在
        if not user:
            return JsonResponse({'code': 400,
                                 'errmsg': '用户名或密码有误'})
        #8. 状态保持
        login(request, user)
        #9. 判断是否需要记住用户
        if remembered != True:
            # 11. 如果不需要:设置session有效期:关闭浏览器立刻过期
            request.session.set_expiry(0)
        else:
        #10. 如果需要:设置session有效期:两周
            request.session.set_expiry(None)

        response = JsonResponse({'code':0,
                             'errmsg': 'ok'})

        # 补充: response.set.cookie(key, value, max_age)
        response.set.cookie('username', user.Username, max_age=3600 *24 *14)


        #12. 返回状态
        return response


class LogoutView(View):

    def delete(self, request):
        '''退出登录(删除session和cookie)'''

        #1.删除session信息, logout()
        logout(request)

        response = JsonResponse({'code':0,
                                 'errmsg':'ok'})
        #2. 清楚cookie(username)
        response.delete_cookie()

        #3. 返回结果
        return response


class UserInfoView(LoginRequiredMixin, View):
    '''只有登录用户才能进入该类视图'''

    def get(self, request):
        '''提供个人信息界面'''

        # 获取界面需要的数据,进行拼接
        dict = {'username': request.user.username,
                'mobile': request.user.mobile,
                'email': request.user.email,
                'email_active': request.user.email_active}

        return JsonResponse({'code':0,
                             'errmsg': 'ok',
                             'info_data':dict})

class EmailView(View):

    def put(self, request):
        '''保存email到数据库, 给邮箱发送邮件'''

        #1.接收参数(json)
        dict = json.loads(request.body.decode())
        email = dict.get('email')

        #2.检验参数:判断该参数是否有值
        if not email:
            return JsonResponse({'code':400,
                                 'errmsg':'缺少必传参数'})

        #3. 检验email的格式
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return JsonResponse({'code':400,
                                 'errmsg':'email格式不对'})

        try:
            #4. 把前端发送的email赋值给当前用户
            request.user.email = email
            #5. 保存
            request.user.save()
        except Exception as e:
            return JsonResponse({'code': 400,
                                 'errmsg': '保存邮箱失败'})

        # 变换 email 的格式: 从 '123456@qq.com' 变为: '<123456@qq.com>'
        email = '<' + email + '>'



        #6. 给当前邮箱发送一封信
        verify_url = request.user.generate_access_token()
        send_verify_email.delay(email, verify_url)


        #7. 返回json参数
        return JsonResponse({'code': 0,
                             'errmsg': 'ok'})

class VerifyEmailView(View):
    def put(self, request):
        '''获取前端传入的token,更改用户的email_active为true'''


        #接收参数
        token = request.GET.get('token')
        #校验参数,判断token是否为空和过期,提取user
        if not token:
            return JsonResponse({'code':400,
                                 'errmsg':'token为空'})


        #调用上面封装好的方法,将token传入
        user = User.check_access_token(token)

        if not user:
            return JsonResponse({'code':400,
                                 'errmsg':'token错误'})

        # 修改email_active的值为true
        try:
            user.email = True
            user.save()
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'修改数据库错误'})

        #返回邮箱验证结果
        return JsonResponse({'code':0,
                             'errmsg':'ok'})














class CreateAddressView(View):
    '''新增地址'''

    def post(self, request):
        '''实现新增地址逻辑'''


        try:
            # 1.从mysql中获取该用户的所有没有删除的地址个数
            count = Address.objects.filter(user=request.user, is_delected=False).count()

        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'获取该用户的地址信息出错'})

        #2. 判断该个数是否大于等于20, 如果是, 返回
        if count >= 20:
            return JsonResponse({'code': 400,
                                 'errmsg': '地址个数超过了20个'})

        #3. 接收参数(json)
        dict = json.loads(request.body.decode())
        receiver = dict.get('receiver')
        province_id = dict.get('province_id')
        city_id = dict.get('city_id')
        district_id = dict.get('district_id')
        place = dict.get('place')
        mobile = dict.get('mobile')
        tel = dict.get('tel')
        email = dict.get('email')

        #4. 总体检验
        if not all(receiver, province_id, city_id, district_id, place, mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})

        #5. 单个检验mobile
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '参数mobile有误'})

        #6. tel
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({'code':400,
                                     'errmsg':'参数tel有误'})

        #7. email
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数email有误'})

        try:
            #8. 往Address表中增加地址信息
            address = Address.objects.create(
                user = request.user,
                province_id = province_id,
                city_id = city_id,
                district_id = district_id,
                title = receiver,
                receiver = receiver,
                place = place,
                mobile = mobile,
                tel = tel,
                email = email

            )


            #9. 判断默认地址是否存在,如果不存在,把刚刚新增的地址作为默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'增加地址失败'})

        #10. 拼接参数,返回
        dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'address':dict})


class AddressView(View):

    def get(self, request):
        '''前端发送get请求, 获取地址信息的接口'''

        try:
            #1. 从mysql中获取该用户的所有未删除的地址信息
            addresses = Address.objects.filter(user=request.user,
                                            is_deleted=False)
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'从地址表中获取不到地址信息'})

        list = []

        #2. 遍历这些地址信息,获取每一个地址
        for address in addresses:

        #3. 把每一个地址信息 ====> {} === []
            dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }

            if request.user.default_address.id == address.id:
                #默认地址
                # 4. 判断该地址信息是否默认地址， 如果是，增加到【】的第一个
                list.insert(0, dict)
            else:
                #5. 如果不是，追加到【】的后面
                list.append(dict)

        default_address_id = request.user.default_address.id

        #6.拼接参数，返回json

        return JsonResponse({'code':0,
                             'errmsg':'ok',
                             'default_address_id':default_address_id,
                             'addresses':list})



class UpdateDestroyAddressView(View):

    def put(self,request, address_id):
        '''修改地址的接口'''

        #1. 接收前端传入的数据
        dict = json.loads(request.body.decode())
        receiver = dict.get('receiver')
        province_id = dict.get('province_id')
        city_id = dict.get('city_id')
        district_id = dict.get('district_id')
        place = dict.get('place')
        mobile = dict.get('mobile')
        tel = dict.get('tel')
        email = dict.get('email')


        #2. 检验数据
        if not all(receiver, province_id, city_id, district_id, place, mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '缺少必传参数'})

        # 5. 单个检验mobile
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return JsonResponse({'code': 400,
                                 'errmsg': '参数mobile有误'})

        # 6. tel
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数tel有误'})

        # 7. email
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return JsonResponse({'code': 400,
                                     'errmsg': '参数email有误'})

        #3. 获取address_id对应的查询集，调用查询集的 update方法，更新
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                title=receiver,
                receiver=receiver,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )

            address = Address.objects.get(id=address_id)

        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'更新失败'})


        #4. 拼接参数返回
        dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return JsonResponse({'code': 0,
                             'errmsg': 'ok',
                             'address': dict})


    def delete(self, request, address_id):
        '''删除address_id对应的地址'''

        try:
            #1.根据地址的id获取地址
            address = Address.objects.get(id=address_id)

            #2. 删除该地址对象
            #错误的写啊，不建议这么写：address.deleted()
            address.is_deleted = True

            #3. 保存
            address.save()
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'删除失败'})

        #4. 返回结果
        return JsonResponse({'code':0,
                             'errmsg':'ok'})



class DefaultAddressView(View):
    '''设置默认地址'''

    def put(self, request, address_id):
        '''更改默认地址'''

        try:
            address = Address.objects.get(id=address_id)

            # 把address_id更改到默认地址
            # request.user.default_address_id = address_id

            request.user.default_address_id = address.id

            # 保存
            request.user.save()
        except Exception as e:
            return JsonResponse({'code': 400,
                                 'errmsg': '设置默认地址出错'})

        return JsonResponse({'code': 0,
                             'errmsg': 'ok'})



class ChangeAddressTitleView(View):
    '''设置地址标题'''

    def put(self, request, address_id):
        '''获取对应id的地址， 更改该地址的标题'''

        #1.接收json传参
        dict = json.loads(request.body.decode())
        title = dict.get('title')

        #2.根据id获取对应的地址
        try:
            # address = Address.objects.get(id=address_id)
            #
            # #3.更改改地址的标题
            # address.title = title
            #
            # #4.保存
            # address.save()

            Address.objects.filter(id=address_id).update(
                title=title
            )

        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'修改失败'})

        #5.返回
        return JsonResponse({'code': 0,
                             'errmsg': 'ok'})


class ChangePasswordView(LoginRequiredMixin, View):
    '''修改密码'''

    def put(self, request):
        '''修改密码端口'''

        #1.接收参数json
        dict = json.loads(request.body.decode())
        old_password = dict.get('old_password')
        new_password = dict.get('new_password')
        new_password2 = dict.get('new_password2')

        #2.总体检验是否为空
        if not all(new_password, old_password, new_password2):
            return JsonResponse({'code':400,
                                 'errmsg':'必传参数为空'})

        #3. 对比老的密码，获取结果
        result = request.user.check_password(old_password)

        #4. 查看结果是否为True， 如果不为True，返回
        if not result:
            return JsonResponse({'code':400,
                                 'errmsg':'老密码有问题'})

        #5. 单个检验新密码
        if not re.macth(r'^[0-9A-Za-z]{8,20}$', new_password):
            return JsonResponse({'code':400,
                                 'errmsg':'密码最少8位,最长20位'})

        #6. 检验新密码和确认密码是否一致
        if new_password != new_password2:
            return JsonResponse({'code':400,
                                 'errmsg':'两次密码不一样'})

        try:
            #7. 把当前用户的密码设置为新密码
            request.user.set_password(new_password)
            #8. 保存结果
            request.save()
        except Exception as e:
            return JsonResponse({'code':400,
                                 'errmsg':'保存失败'})

        #9. 返回响应

        return JsonResponse({'code':0,
                             'errmsg':'ok'})
