from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from .models import Area

# Create your views here.
class ProvinceView(View):

    def get(self, request):
        '''前端发送请求,获取省份数据'''
        try:
            #1. 查询省级数据
            province_model_list = Area.objects.filter(parent__isnull=True)

            #创建一个list
            list = []

            #2. 整理省级数据
            for province in province_model_list:
                list.append({
                    'id': province.id,
                    'name': province.name
                })
        except Exception as e:

            #如果报错,则返回错误原因
            return JsonResponse({'code':400,
                                 'errmsg':'获取省份数据出错'})

        #3. 返回整理好的省级数据
        return JsonResponse({'code':0,
                             'errmsg':'ok',
                             'province_list':list})

