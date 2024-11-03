# -*- coding: utf-8 -*-

from odoo import fields, models


class res_company(models.Model):
    """
    Overwrite to keep settings in company
    """
    _inherit = "res.company"

    kpi_history_tolerance = fields.Integer(
        string="History Tolerance",
        default=3,
    )
    show_kpi_help = fields.Boolean(
    	string="Show Help Tabs",
    	default=True,
    )
