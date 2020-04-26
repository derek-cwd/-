from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
# Create your views here.
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
import logging, random
logger = logging.getLogger('django')

from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from celery_tasks.sms.tasks import send_sms_verify_code




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


class SMScodeView(View):

    def get(self, request, mobile):
        '''接受参数,检验,发送短信验证码'''

        #0. 从redis中获取60s保存的信息
        redis_conn = get_redis_connection('verify_code')
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        #0.1 判断该信息是否存在,如果不存在, 进行下面的步骤,如果存在,返回
        if send_flag:
            return JsonResponse({'code': 400,
                                 'errmsg': '发送短信过于频繁'})

        #1.接收查询字符串
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        #2.总体检验(查看参数是否为空)
        if not all([image_code_client, uuid]):
            return JsonResponse({'code':400,
                                  'errmsg': '必传参数不能为空'})

        #3. 链接redis,获取redis的连接对象
        # 挪到上面去了

        #4.从redis中取出图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)

        #5. 判断服务器的图形验证码是否过期,如果过期,return
        if image_code_server is None:
            return JsonResponse({'code':400,
                                 'errmsg': '图形验证码过期'})

        #6. 删除redis中图形验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logger.info(e)

        #7. 对比前后端的图形验证码
        if image_code_client.lower() != image_code_server.decode().lower():
            return JsonResponse({'code':400,
                                 'errmsg': '输入的图形验证码出错'})

        #8. 随机生成6位的短信验证码
        sms_code = '%06d' % random.randint(0, 999999)

        #9. 打印短信验证码
        logger.info(sms_code)

        #创建redis管道:

        p1 = redis_conn.pipeline()

        #10. 把短信验证码保存到redis
        p1.setex('sms_%s' % mobile, 300, sms_code)
        p1.setex('send_flag_%s' % mobile, 60, 1)

        #执行管道
        p1.excute()

        #11. 调用容联云,发送短信验证码
        # CCP().send_template_sms(mobile, [sms_code, 5], 1)

        #添加一个提示celery抛出任务的提醒
        send_sms_verify_code.delay(mobile, sms_code)

        #12. 返回json
        return JsonResponse({'code':0,
                             'errmsg':'ok'})