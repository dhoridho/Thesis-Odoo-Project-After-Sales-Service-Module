
from cgi import FieldStorage
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShSplitRfqWizard(models.TransientModel):
    _inherit = 'sh.split.rfq.wizard'
    
    ps_order_ids = fields.One2many('purchase.order.split', 'split_id', string="Purchase Order Line")
        
    @api.model
    def default_get(self, fields):
        res = super(ShSplitRfqWizard, self).default_get(fields)
        context = dict(self.env.context) or {}
        purchase_order_id = self.env['purchase.order'].browse(context.get('active_ids'))
        data = []
        for line in purchase_order_id.order_line:
            vals = {
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'purchase_line_id': line.id,
                    'sequence': line.sequence2,
                    'product_template_id': line.product_template_id.id,
                    'name': line.product_template_id.name,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'date_planned': line.date_planned,
                    'destination_warehouse_id': line.destination_warehouse_id.id
                    }
            data.append((0, 0, vals))
        res["ps_order_ids"] = data
        return res
    
    def action_split(self):
        active_id = self.env.context.get('active_id')
        active_po = self.env['purchase.order'].sudo().browse(active_id)
        
        if self.split_by == 'new':
            do_unlink = False
            new_purchase_order_id = False
            data = []
            for line in self.ps_order_ids:
                if line.tick:
                    do_unlink = True
                    vals = {
                        'product_id': line.product_id.id,
                        'sequence2': line.sequence,
                        'product_template_id': line.product_template_id.id,
                        'name': line.product_template_id.name,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'date_planned': line.date_planned,
                        'destination_warehouse_id': line.destination_warehouse_id.id,
                        'analytic_tag_ids': [(6, 0, active_po.analytic_account_group_ids.ids)],
                        'product_uom': line.product_uom.id
                    }
                    data.append((0, 0, vals))
            if do_unlink:
                new_purchase_order = active_po.copy({
                    'order_line': data
                })
                new_purchase_order_id = new_purchase_order
            if new_purchase_order_id:
                return{
                    'name': 'RFQ',
                    'res_model': 'purchase.order',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_id': new_purchase_order_id.id,
                    'domain': [('id', '=', new_purchase_order_id.id)],
                    'target': 'current',
                }
                
        elif self.split_by == 'existing':
            for line in self.ps_order_ids:
                data = []
                if line.tick:
                    purchase_order_line = self.purchase_order_id.order_line.filtered(lambda m: m.product_template_id.id == line.product_template_id.id)
                    if purchase_order_line:
                        purchase_order_line.product_qty += line.product_qty
                    else:
                        vals = {
                            'sequence2': line.sequence,
                            'product_id': line.product_id.id,
                            'product_template_id': line.product_template_id.id,
                            'name': line.product_template_id.name,
                            'product_qty': line.product_qty,
                            'price_unit': line.price_unit,
                            'date_planned': line.date_planned,
                            'destination_warehouse_id': line.destination_warehouse_id.id,
                            'analytic_tag_ids': [(6, 0, active_po.analytic_account_group_ids.ids)],
                            'product_uom': line.product_uom.id
                        }
                        data.append((0, 0, vals))
                        self.purchase_order_id.order_line = data

class PurchaseOrderSplit(models.TransientModel):
    _name = 'purchase.order.split'
    _description = "Purchase Order Split"
    
    tick = fields.Boolean(string="Tick")
    sequence = fields.Char(string="Sequence")
    product_template_id = fields.Many2one('product.template', string='Product')
    name = fields.Text(string="Description")
    date_planned = fields.Datetime(string="Expected Date")
    product_qty = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Unit Price")
    destination_warehouse_id = fields.Many2one('stock.warehouse', string="Destination")
    split_id = fields.Many2one('sh.split.rfq.wizard')
    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase Order")
    product_uom = fields.Many2one('uom.uom', string="Uom")
    product_id = fields.Many2one('product.product', string="Product")
    