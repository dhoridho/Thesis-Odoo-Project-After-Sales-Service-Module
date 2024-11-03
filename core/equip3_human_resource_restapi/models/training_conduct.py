from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "training.conduct"
class HRTrainingConduct(models.Model):
    _inherit = 'training.conduct'

    def action_approve(self):
        res =  super(HRTrainingConduct,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        for data in self.conduct_line_ids:
            if data.employee_id.user_id.firebase_token:
                fireBaseNotification.sendPush("Approval of Leave Request","Your Leave Request has been approved.",eval(data.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRTrainingConduct,self).action_refuse()
        obj = {'module':module,'id':f"{self.id}"}
        for data in self.conduct_line_ids:
            if data.employee_id.user_id.firebase_token:
                fireBaseNotification.sendPush("Rejection of Training Conduct","Your Training Conduct has been Rejected.",eval(data.employee_id.user_id.firebase_token),obj) 
        return res
        