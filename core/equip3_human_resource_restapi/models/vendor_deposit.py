from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "vendor.deposit"
class VendorDeposit(models.Model):
    _inherit = 'vendor.deposit'

    def action_approve(self):
        res =  super(VendorDeposit,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Cash Advandces Request","Your cash advance request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(VendorDeposit,self).action_refuse()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection Cash Advandces Request","Your cash advance request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        