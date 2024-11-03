from odoo import models,fields,api


class ConstructionDashboard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    @api.model
    def set_dashboard_icon(self):
            menu_id = self.env['ir.ui.menu'].search([
                ('name', 'ilike', 'dashboard'),
                ('parent_id', '=', self.env.ref('abs_construction_management.construction_management').id)
            ], limit=1)
            if menu_id:
                menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-purchase-purchase-dashboard'})


    @api.model
    def set_dashboard_icon_internal(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('equip3_construction_masterdata.construction_internal_project').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-purchase-purchase-dashboard'})


class KsDashboardNinjaItemAdvance(models.Model):
    _inherit = "ks_dashboard_ninja.item"

    ks_icon_select = fields.Char(
        string="Icon Option", default="Custom", help="Choose the Icon option. "
    )
