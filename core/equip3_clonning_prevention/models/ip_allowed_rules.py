from odoo import models, fields, api

class ipAllowedRules(models.Model):
    _name = 'ip.allowed.rules'

    name = fields.Char()
    active_rules = fields.Boolean()
    rule_line_ids = fields.One2many('ip.allowed.rules.line', 'rule_id')
    
    
    def action_update_ip_rules(self):
         return {
            'type': 'ir.actions.act_window',
            'res_model': 'update.ip.rules',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Update IP Rules",
            'target': 'new',
            'context':{'default_source':'database','default_ip_rule_id':self.id},
        }


class ipAllowedRulesLine(models.Model):
    _name = 'ip.allowed.rules.line'

    rule_id = fields.Many2one('ip.allowed.rules')
    name = fields.Char()
