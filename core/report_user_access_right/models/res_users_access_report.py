# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsersAccessReportRecord(models.Model):
    _name = 'res.users.access.report.record'

    sl_no = fields.Integer(string='Sl')
    user_id = fields.Many2one('res.users', string='User')
    login = fields.Char()
    user_active = fields.Boolean()

    column1 = fields.Boolean()
    column2 = fields.Boolean()
    column3 = fields.Boolean()
    column4 = fields.Boolean()
    column5 = fields.Boolean()

    column6 = fields.Boolean()
    column7 = fields.Boolean()
    column8 = fields.Boolean()
    column9 = fields.Boolean()
    column10 = fields.Boolean()

    column11 = fields.Boolean()
    column12 = fields.Boolean()
    column13 = fields.Boolean()
    column14 = fields.Boolean()
    column15 = fields.Boolean()

    def open_user_form(self):
        self.ensure_one()

        return {
            'name': self.user_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.user_id.id,
            'res_model': 'res.users',
            'target': 'new',
            'views': [[self.env.ref('base.view_users_form').id, 'form']],
        }




