from odoo import fields, models, api, _


class UomConversionHistory(models.Model):
    _name = "uom.conversion.history"
    _description = 'UoM Conversion History'
    _order = "product_id,uom_id"

    product_id = fields.Many2one('product.product', string='Product', required=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True)
    prod_lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number', check_company=True, domain="[('product_id','=',product_id)]")
    package_id = fields.Many2one('stock.quant.package', 'Package',domain="[('location_id', '=', location_id)]")
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_qty = fields.Float('Counted',digits='Product Unit of Measure', default=0)
    uom_id = fields.Many2one('uom.uom', string='UOM',required=True)
    counted_qty = fields.Float('Counted Conversion' ,digits='Product Unit of Measure', default=0)
    uom_conversion = fields.Many2one('uom.uom', string='UOM conversion',required=True)
    si_uom_id = fields.Many2one('stock.inventory', string="Inventory Adjustments")

    # def write(self, vals):
    #     set_uom = set()
    #     for x in self.si_uom_id.line_ids:
    #         set_uom.add(x.uom_id)

    #     for uom in set_uom:
    #         uom_quantity = 0
    #         for line in self.si_uom_id.line_ids:
    #             if uom.id == line.uom_id.id:
    #                 uom_quantity += line.product_qty
    #         print('id sama brooooooooooooo',uom_quantity)
