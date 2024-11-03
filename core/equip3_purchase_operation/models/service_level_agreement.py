from odoo import api , fields , models

class ServiceLevelAgreement(models.Model):
    _name = 'service.level.agreement'
    _inherit = 'term.condition'
    _description = 'Service Level Agreement'

