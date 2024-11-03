# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models

class PosXReport(models.TransientModel):
    _name = "x.report.wizard"
    _description = "POS X Report Wizard"


    pos_session_ids = fields.Many2many('pos.session', 'pos_sessions',string="POS Session(s)",domain="[('state', 'in', ['opened'])]",required=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
    report_type = fields.Char('Report Type', readonly = True, default='PDF')

    def generate_x_report(self):
        data = {'session_ids':self.pos_session_ids.ids}
        return self.env.ref('equip3_pos_report.action_x_report_print').report_action([], data=data)