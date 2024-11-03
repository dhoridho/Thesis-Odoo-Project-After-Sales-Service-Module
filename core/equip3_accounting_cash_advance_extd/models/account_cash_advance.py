# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, exceptions, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_employee_cash_adv = fields.Boolean(string='Is An Employee')
