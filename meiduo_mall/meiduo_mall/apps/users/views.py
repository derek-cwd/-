from django.http import JsonResponse
from django.shortcuts import render


# Create your views here.
from django.views import View

from users.models import User


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