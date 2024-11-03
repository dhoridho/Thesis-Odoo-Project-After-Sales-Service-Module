# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Company(models.Model):
    _inherit = "res.company"

    company_npwp = fields.Char('Company NPWP')
    work_unit = fields.Char('Work Unit')
    corporate_id = fields.Char('Company ID')