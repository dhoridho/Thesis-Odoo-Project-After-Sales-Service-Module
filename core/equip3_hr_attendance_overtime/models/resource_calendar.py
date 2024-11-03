from odoo import api,fields,models



class Equip3OvertimeRules(models.Model):
    _inherit = 'resource.calendar'
    overtime_rules_id = fields.Many2one('overtime.rules')