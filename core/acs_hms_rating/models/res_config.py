# -*- coding: utf-8 -*-
# Part of AlmightyCS See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    appointment_rating_mail_template = fields.Many2one('mail.template', 'Appointment Rating Mail Template',
        help="This will set the default mail template for Appointment Rating Request.")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appointment_rating_mail_template = fields.Many2one('mail.template', 
        related='company_id.appointment_rating_mail_template',
        string='Appointment Rating Mail Template',
        help="This will set the default mail template for Appointment Rating Request.", readonly=False)