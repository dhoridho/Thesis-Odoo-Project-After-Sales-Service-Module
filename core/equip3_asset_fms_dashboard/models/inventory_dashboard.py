from odoo import models,fields,api


class InventoryDashboard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('maintenance.menu_maintenance_title').id)
        ])
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-inventory-inventory-dashboard'})

        fms_dashboard_menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('equip3_asset_fms_restructure_menu.maintenance_menu_fms_title').id)
        ])
        if fms_dashboard_menu_id:
            fms_dashboard_menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-inventory-inventory-dashboard'})    

    @api.model
    def _setup_complete(self):
        super(InventoryDashboard, self)._setup_complete()
        self.set_dashboard_icon()