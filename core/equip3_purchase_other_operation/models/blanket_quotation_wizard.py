
from odoo import api, fields, models, _
from odoo.exceptions import UserError , ValidationError


class BlanketQuotation(models.TransientModel):
    _name = 'blanket.quotation'
    _description = "Blanket Quotation"

    wiz_line_ids = fields.One2many('blanket.quotation.line','bq_id')

    @api.model
    def default_get(self, fields):
        res = super(BlanketQuotation, self).default_get(fields)
        active_ids=self._context.get('active_ids')
        invoice_order_ids=self.env['purchase.requisition'].browse(active_ids)
        split_order_lines=[]
        for order in invoice_order_ids:
            for line in order.line_ids:
                split_order_lines.append((0,0, {
                    'vendor_id': order.vendor_id.id,
                    'product_id':line.product_id.id,
                    'remaining_quantity':line.qty_remaining,
                    'new_quatation_quantity':line.qty_remaining,
                    'blanket_order_line_id':line.id,
                    'unit_of_measure_id':line.product_uom_id.id,
                    'unit_price':line.price_unit,
                    'is_goods_orders': line.is_goods_orders,
                    'subtotal':0,
                }))
        res.update({
            'wiz_line_ids': split_order_lines
        })

        return res

    def create_quatation(self):
        line_order_id = self.env['purchase.requisition'].browse(self.env.context.get('active_ids'))
        vals = []
        vals_order_line = []
        vendor_id = False
        picking_type = False
        picking_type_line = False
        check_qty = 0
        context = dict(self.env.context) or {}
        for rec in self.wiz_line_ids:
            check_qty += rec.new_quatation_quantity
            if not check_qty:
                continue
            if rec.new_quatation_quantity > rec.remaining_quantity:
                raise ValidationError("Quotation quantity cannot be more than remaining quantity. ")
            picking_type_line = rec.blanket_order_line_id.destination_warehouse.in_type_id.id
            picking_type = rec.blanket_order_line_id.requisition_id.destination_warehouse.in_type_id.id
            vendor_id = rec.vendor_id.id
            line_vals = {
                'product_id': rec.product_id.id,
                'product_qty':rec.new_quatation_quantity,
                'product_uom':rec.unit_of_measure_id.id,
                'price_unit':rec.unit_price,
                'picking_type_id': picking_type_line,
                'analytic_tag_ids': [(6, 0, rec.blanket_order_line_id.account_tag_ids.ids)],
                'price_subtotal':rec.unit_price * rec.new_quatation_quantity,
                'requisition_line_id': rec.blanket_order_line_id.id,
                'destination_warehouse_id': rec.blanket_order_line_id.destination_warehouse.id
            }
            if context.get('goods_order') or line_order_id.is_goods_orders:
                line_vals.update({
                    'is_goods_orders': rec.is_goods_orders
                    })
            elif context.get('services_good') or line_order_id.is_services_orders:
                line_vals.update({
                    'is_services_orders': rec.is_services_orders
                    })
            elif context.get('assets_orders') or line_order_id.is_assets_orders:
                line_vals.update({
                    'is_assets_orders': rec.is_assets_orders
                    })
            elif context.get('rentals_orders') or line_order_id.is_rental_orders:
                line_vals.update({
                    'is_rental_orders': True
                })
            # vals.append((0, 0, line_vals))
            vals_order_line.append(line_vals)
            store=rec.blanket_order_line_id.qty_remaining - rec.new_quatation_quantity
            rec.blanket_order_line_id.write({'qty_remaining':store})
        if not check_qty:
            raise ValidationError("Quotation quantity cannot be zero.")
        if vals_order_line:
            vals = {
                'requisition_id': line_order_id.id,
                'partner_id':vendor_id,
                'branch_id' : line_order_id.branch_id.id,
                'date_order' : line_order_id.date_end,
                'company_id': line_order_id.company_id.id,
                'currency_id': line_order_id.currency_id.id,
                'analytic_account_group_ids': [(6, 0, line_order_id.account_tag_ids.ids)],
                'picking_type_id':picking_type,
                'destination_warehouse_id': line_order_id.destination_warehouse.id,
                # 'order_line' : vals,
                'origin': line_order_id.name,
                'from_bo': True
            }
            if context.get('goods_order') or line_order_id.is_goods_orders:
                vals.update({
                    'is_goods_orders': line_order_id.is_goods_orders
                    })
            elif context.get('services_good') or line_order_id.is_services_orders:
                vals.update({
                    'is_services_orders': line_order_id.is_services_orders
                    })
            elif context.get('assets_orders') or line_order_id.is_assets_orders:
                vals.update({
                    'is_assets_orders': line_order_id.is_assets_orders
                    })
            elif context.get('rentals_orders') or line_order_id.is_rental_orders:
                vals.update({
                    'is_rental_orders': True
                })
            purchase_order_id = self.env['purchase.order'].create(vals)
            for line in vals_order_line:
                line['order_id'] = purchase_order_id.id
            self.env['purchase.order.line'].create(vals_order_line)
            purchase_order_id._onchange_partner_invoice_id()

            if purchase_order_id and line_order_id.bo_state != 'ongoing':
                line_order_id.bo_state = 'ongoing'
            return {
                'type': 'ir.actions.act_window',
                'name': 'Request for Quotations',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'domain' : [('requisition_id','=',line_order_id.id)],
                'target': 'current'
            }

class BlanketQuotationLine(models.TransientModel):
    _name = 'blanket.quotation.line'
    _description = "Blanket Quotation Line"

    bq_id = fields.Many2one('blanket.quotation', required=True, string='Blanket Quotation', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    remaining_quantity = fields.Float(string="Remaining Quantity")
    new_quatation_quantity = fields.Float(string="New Quotation Quantity")
    blanket_order_line_id=fields.Many2one('purchase.requisition.line',string="BO Line")
    unit_of_measure_id=fields.Many2one('uom.uom',string="Unit of Measure")
    unit_price=fields.Float(string="Unit Price")
    subtotal=fields.Float(string="Subtotal")
    is_goods_orders = fields.Boolean(string="Goods Orders", default=False)
    is_services_orders = fields.Boolean(string="Services Orders", default=False)
    