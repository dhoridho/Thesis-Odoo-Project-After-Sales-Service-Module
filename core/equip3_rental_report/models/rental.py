from odoo import models,fields,api

class RentalOrderLineInherit(models.Model):
    _inherit = 'rental.order.line'

    product_categ_id = fields.Many2one('product.category', related="product_id.categ_id" ,string='Product Category', required=True, store=True)
    order_date = fields.Datetime(string='Order Date', related="rental_id.date_order", store=True)
    branch_id = fields.Many2one('res.branch', related='product_id.branch_id', string="Branch")

class RentalOrder(models.Model):
    _inherit = 'rental.order'

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('equip3_rental_masterdata.menu_rental_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-sales-sales-dahboard'})
class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

class RentalInheritReturnOfAssets(models.Model):
    _inherit = 'return.of.assets'

    branch_id = fields.Many2one('res.branch', related='product_template_id.branch_id', string="Branch")
