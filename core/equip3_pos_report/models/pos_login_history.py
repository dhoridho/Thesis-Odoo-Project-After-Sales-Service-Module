# -*- coding: utf-8 -*-

from odoo import fields, models

class PosLoginHistory(models.Model):
    _name = "pos.login.history"
    _description = "Pos Login History"
    _order = "checkin_datetime asc"

    user_id = fields.Many2one('res.users', string='Cashier')
    pos_config_id = fields.Many2one('pos.config', string='Point of Sale')
    pos_branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    checkin_datetime = fields.Datetime('Check in Date')
    checkout_datetime = fields.Datetime('Check out Date')
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)

    def generate_data_group_by_branch(self):
        data = defaultdict(list)
        for rec in self:
            data[rec.pos_branch_id].append(rec)
        return data

    def generate_report(self):
        data = self.env['pos.login.history'].search([('checkin_datetime','>=',self.start_datetime),('checkout_datetime','<=',self.end_datetime)])        
        if not data:
            raise UserError(_('No have data to print.'))
        return self.env.ref('equip3_pos_report.act_report_pos_login_history_report').report_action(data)
