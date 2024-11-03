from odoo import models, api, fields, _, sql_db


class KsDashboardNinjaItemAdvance(models.Model):
    _inherit = "ks_dashboard_ninja.item"

    ks_icon_select = fields.Char(
        string="Icon Option", default="Custom", help="Choose the Icon option. "
    )
