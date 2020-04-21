from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
# Create your views here.
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection

class ImageCodeView(View):

    def get(self, request, uuid):
        '''生成图形验证码,保存到redis中, 返回图片
        :param request:请求对象
        :param uuid: 浏览器端生成的唯一id
        return:一个图片
        '''

        #1. 调用工具类 captcha 生成图形验证码
        text, image = captcha.generate_captcha()

        #2. 链接redis,获取连接对象
        redis_conn = get_redis_connection('verify_code')

        #3.利用连接对象,保存数据到redis, 使用setex函数
        #redis_conn.setex('<key>', '<expire>', '<value>')

        redis_conn.setex('imag_%s' % uuid, 300, text)

        #4. 返回图片

        return HttpResponse(image,
                            content_type='image/jpg')
