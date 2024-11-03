from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.full.loan.payment"
class HRFullLoanPayment(models.Model):
    _inherit = 'hr.full.loan.payment'

    def action_approved(self):
        res =  super(HRFullLoanPayment,self).action_approved()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Multiple Payment","Your multiple payment request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_rejected(self):
        res =  super(HRFullLoanPayment,self).action_rejected()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Multiple Payment","Your multiple payment request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        