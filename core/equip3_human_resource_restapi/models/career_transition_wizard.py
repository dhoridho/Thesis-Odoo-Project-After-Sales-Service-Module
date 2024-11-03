from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.career.transition"
class HROvertimeRequestApprovalWizard(models.TransientModel):
    _inherit = 'career.transition.wizard'

    def submit(self):
        res =  super(HROvertimeRequestApprovalWizard,self).submit()
        obj = {'module':module,'id':f"{self.transition_id.id}"}
        if self.state == "approve":
            fireBaseNotification.sendPush("Approval of Career Transition Request","Your Career Transition Request has been approved.",eval(self.transition_id.employee_id.user_id.firebase_token),obj) 
                            
        if self.state == "rejected":
            fireBaseNotification.sendPush("Rejection of Career Transition Request","Your Career Transition Request has been rejected.",eval(self.transition_id.employee_id.user_id.firebase_token),obj)
        return res