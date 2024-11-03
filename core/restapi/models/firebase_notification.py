from odoo.http import request
from odoo.exceptions import ValidationError
import firebase_admin
from firebase_admin import credentials, messaging
from odoo.modules import get_module_path

class fireBaseNotification(object):
    def sendPush(title, msg, registration_token, dataObject=None):
        module_path = get_module_path('restapi')
        cred = credentials.Certificate(f"{module_path}/token/hrm-notification-82dc7-firebase-adminsdk-r9qur-7ed227c01f.json")
        try:
            firebase_admin.get_app()
        except ValueError as e:
            firebase_admin.initialize_app(cred)
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=msg
            ),
            data=dataObject,
            tokens=registration_token,
        )
        response = messaging.send_multicast(message)
        print('Successfully sent message:', response)