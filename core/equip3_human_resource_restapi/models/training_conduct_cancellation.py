from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.training.conduct.cancellation"
class HRTrainingConductCancellation(models.Model):
    _inherit = 'hr.training.conduct.cancellation'

    def action_approve(self):
        res =  super(HRTrainingConductCancellation,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        for data in self.conduct_cancell_line_ids:
            if data.employee_id.user_id.firebase_token:
                fireBaseNotification.sendPush("Approval of Training Conduct Cancellation","Your Training Conduct Cancellation has been Approved.",eval(data.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRTrainingConductCancellation,self).action_refuse()
        obj = {'module':module,'id':f"{self.id}"}
        for data in self.conduct_cancell_line_ids:
            if data.employee_id.user_id.firebase_token:
                fireBaseNotification.sendPush("Rejection of Training Conduct Cancellation","Your Training Conduct Cancellation has been Rejected.",eval(data.employee_id.user_id.firebase_token),obj) 
        return res
        