from celery_tasks.main import celery_app
from celery_tasks.yuntongxun.ccp_sms import CCP


@celery_app.task(name='send_sms_verify_code')
def send_sms_verify_code(mobile, sms_code):
    '''在celery中实现短信的异步发送功能'''

    result = CCP().send_template_sms(mobile, [sms_code, 5], 1)

    print(result)

    return result