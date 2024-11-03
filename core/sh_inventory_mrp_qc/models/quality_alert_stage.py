# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShQcAlertStage(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'sh.qc.alert.stage'
    _description = "Quality Alert Stage"

    sh_logged_user = fields.Many2one(
        'res.users', 'Approved By', readonly=False)
    name = fields.Char('Name')
    company_id = fields.Many2one(
        'res.company', string="Company", default=lambda self: self.env.company)
    sequence = fields.Integer(string="Sequence")

    @api.model
    def create(self, values):
        if 'company_id' in values:
            sequence = self.env['ir.sequence'].next_by_code(
                'sh.qc.alert.stage')
            values['sequence'] = sequence
        return super(ShQcAlertStage, self).create(values)
