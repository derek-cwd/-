from django.contrib.auth.models import AbstractUser
from django.db import models
from itsdangerous import TimedJSONWebSignatureSerializer, BadData
from django.conf import settings
# Create your models here.
class User(AbstractUser):

    #增加一个mobile字段

    mobile = models.CharField(max_length=11, unique=True, verbose_name='电话号码')


    #再增加一个字段,email_active 用于记录邮箱是否激活 (4/29)
    email_active = models.BooleanField(default=False,
                                       verbose_name='邮箱是否激活')



    class Meta:
        #指定表名
        db_table = 'tb_users'
        #指定当前表的中文:
        verbose_name = '用户表'
        #如果是复数,则还是verbose_name
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username



    def generate_access_token(self):
        '''生成一个token值,把token和url的前半部分拼接到一起,返回'''

        # TimedJSONWebSignatureSerializer(秘钥, 有效期)
        obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=1800)
        dict = {
            'user_id': self.id,
            'email': self.email

        }

        token = obj.dumps(dict).decode()

        return settings.EMAIL_VERIFY_URL + token

    @staticmethod
    def check_access_token(token):

        #获取对象
        obj = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=1800)

        try:
            dict = obj.loads(token)
        except BadData:
            return None
        else:
            user_id = dict.get('user_id')
            email = dict.get('email')

            try:
                user = User.objects.get(id=user_id,
                                        emsil=email)
            except Exception as e:
                return None
            else:

                return user
