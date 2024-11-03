# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosZReport(models.TransientModel):
	_inherit = "z.report.wizard"


	is_ph_template = fields.Boolean('Philippines Template')


class pos_sale_report(models.TransientModel):
    _inherit = 'pos.sale.report'


    is_ph_template = fields.Boolean('Philippines Template',default=True)
