from odoo import models, fields, api, _


class OverheadTime(models.Model):
    _name = 'overhead.time'
    _description = 'Overhead Time Management'
    _rec_name = 'product'

    product = fields.Many2one('product.product', string='Product')
    mrp_workcenter_id = fields.Many2one('mrp.workcenter', string='Workcenter')


class OverheadMaterial(models.Model):
    _name = 'overhead.material'
    _description = 'Overhead Material Management'
    _rec_name = 'product'

    product = fields.Many2one('product.product', string='Product')
    
    consumed = fields.Float(string='Quantity Consumed/Hour', default=1.0)
    consumed_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    mrp_wc_id = fields.Many2one('mrp.workcenter', string='Workcenter')

    @api.onchange('product')
    def onchange_product(self):
        if self.product and self.product.uom_id:
            self.consumed_uom = self.product.uom_id.id
        else:
            self.consumed_uom = False
