from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "employee.loan.cancelation"
class HREmployeeLoanDetailsCancellation(models.Model):
    _inherit = 'employee.loan.cancelation'

    def action_approved(self):
        res =  super(HREmployeeLoanDetailsCancellation,self).action_approved()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Loan Cancellation Request","Your Loan Cancelation request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_reject(self):
        res =  super(HREmployeeLoanDetailsCancellation,self).action_rejected()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Loan Request"," Your Loan Cancelation request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        