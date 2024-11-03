import pdb
from odoo import models, api, fields


class DashboardIcon(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    @api.model
    def set_dashboard_icon_asset(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('maintenance.menu_maintenance_title').id)
        ])
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-v1-main-asset-control-dashboard'})


    