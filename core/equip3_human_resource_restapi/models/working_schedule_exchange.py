from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification


class HRWorkingScheduleExchange(models.Model):
    _inherit = 'schedule.exchange'
    
    def action_approve(self):
        res =  super(HRWorkingScheduleExchange,self).action_approve()
        obj = {'module':'schedule.exchange','id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Working Schedule Change Request","Your working schedule exchange request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRWorkingScheduleExchange,self).action_refuse()
        obj = {'module':'schedule.exchange','id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Working Schedule Change Request","Your working schedule exchange request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res