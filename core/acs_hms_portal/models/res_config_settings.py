# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class ResCompany(models.Model):
    _inherit = "res.company"

    create_auto_users = fields.Boolean('Create Users For Patients')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    create_auto_users = fields.Boolean(related='company_id.create_auto_users',
        string='Create Users For Patients', readonly=False)
