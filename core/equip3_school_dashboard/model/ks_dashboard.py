from odoo import api, fields, models, _

class KsDashboardNinjaItemAdvance(models.Model):
    _inherit = "ks_dashboard_ninja.item"

    ks_icon_select = fields.Char(
        string="Icon Option", default="Custom", help="Choose the Icon option. "
    )
    