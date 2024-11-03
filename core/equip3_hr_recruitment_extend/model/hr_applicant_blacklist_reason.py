from odoo import models, fields, api, _

class blacklistReason(models.Model):
    _name = "hr.applicant.blacklist.reason"
    
    name = fields.Char()
    
    
class blacklistReasonDescription(models.Model):
    _name = "hr.applicant.blacklist.reason.description"
    _rec_name = 'blacklist_reason_id'
    
    blacklist_reason_id = fields.Many2one('hr.applicant.blacklist.reason')
    description = fields.Text()
    
    