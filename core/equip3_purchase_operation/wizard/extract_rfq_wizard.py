
from odoo import models, fields, api


class ExtractRfqWizard(models.TransientModel):
    _name = 'extract.rfq.wizard'
    _description = 'Extract Rfq Wizard'

    purchase_order_extract_ids = fields.One2many('purchase.order.line.extract', 'extract_id', string="Purchase Order Line")
    
    @api.model
    def default_get(self, fields):
        res = super(ExtractRfqWizard, self).default_get(fields)
        context = dict(self.env.context) or {}
        purchase_order_id = self.env['purchase.order'].browse(context.get('active_ids'))
        data = []
        for line in purchase_order_id.order_line:
            vals = {
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'sequence': line.sequence2,
                    'product_template_id': line.product_template_id.id,
                    'name': line.product_template_id.name,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'date_planned': line.date_planned,
                    'destination_warehouse_id': line.destination_warehouse_id.id
                    }
            data.append((0, 0, vals))
        res["purchase_order_extract_ids"] = data
        return res
    
    def action_extract_rfq(self):
        context = dict(self.env.context) or {}
        purchase_order_id = self.env['purchase.order'].browse(context.get('active_ids'))
        data = []
        for line in self.purchase_order_extract_ids:
            if line.tick:
                vals = {
                    'product_id': line.product_id.id,
                    'sequence2': line.sequence,
                    'product_template_id': line.product_template_id.id,
                    'name': line.product_template_id.name,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'date_planned': line.date_planned,
                    'destination_warehouse_id': line.destination_warehouse_id.id,
                    'analytic_tag_ids': [(6, 0, purchase_order_id.analytic_account_group_ids.ids)],
                    'product_uom': line.product_uom.id
                }
                data.append((0, 0, vals))
        new_purchase_order = purchase_order_id.copy({
            'order_line': data
        })
        new_purchase_order.po_extract_id = purchase_order_id.id
        return{
            'name': 'RFQ',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': new_purchase_order.id,
            'domain': [('id', '=', new_purchase_order.id)],
            'target': 'current',
        }

class PurchaseOrderLineExtract(models.TransientModel):
    _name = 'purchase.order.line.extract'
    _description = 'Purchase Order Line Extract'
    
    sequence = fields.Char(string="Sequence")
    tick = fields.Boolean(string="Select Product")
    product_template_id = fields.Many2one('product.template', string='Product')
    name = fields.Text(string="Description")
    date_planned = fields.Datetime(string="Expected Date")
    product_qty = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Unit Price")
    destination_warehouse_id = fields.Many2one('stock.warehouse', string="Destination")
    extract_id = fields.Many2one('extract.rfq.wizard')
    product_id = fields.Many2one('product.product', string="Product")
    product_uom = fields.Many2one('uom.uom', string="Uom")