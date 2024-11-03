from odoo import models,fields,api


class InventoryDashboard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    @api.model
    def set_dashboard_icon(self):
            menu_id = self.env['ir.ui.menu'].search([
                ('name', 'ilike', 'inventory dashboard'),
                ('parent_id', '=', self.env.ref('stock.menu_stock_root').id)
            ])
            if menu_id:
                menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-inventory-inventory-dashboard'})