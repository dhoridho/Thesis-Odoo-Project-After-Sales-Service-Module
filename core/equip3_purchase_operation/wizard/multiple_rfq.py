
from odoo import _, api, fields, models
from datetime import datetime

class MultipleRfq(models.TransientModel):
    _name = "multiple.rfq"
    _description = "Multiple Rfq"

    vendor_ids = fields.Many2many("res.partner", string="Vendor")
    product_ids = fields.Many2many("product.product", string="Products")

    @api.onchange('vendor_ids')
    def _onchange_vendor_ids(self):
        context = dict(self.env.context) or {}
        if context.get('is_goods_order'):
            return {'domain': {'product_ids': [('type', 'in', ('consu','product'))]}}
        elif context.get('services_good'):
            return {'domain': {'product_ids': [('type', '=','service')]}} 

    @api.model
    def _get_default_picking_type(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        return self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', company_id),
        ], limit=1).id

    def create_rfq(self):
        context = dict(self.env.context) or {}
        new_order_id = []
        for rec in self:
            for vendor_id in rec.vendor_ids:
                vals = {
                    'partner_id' : vendor_id.id,
                    'picking_type_id': rec._get_default_picking_type(),
                    'branch_id': self.env.context['allowed_branch_ids'][0],
                    'date_order': datetime.now()
                }
                if context.get('is_goods_order'):
                    context.update({'goods_order': True})
                    vals.update({'is_goods_orders': True})
                elif context.get('services_good'):
                    context.update({'services_good': True})
                    vals.update({'is_services_orders': True})
                elif context.get('assets_orders'):
                    context.update({'assets_orders': True})
                    vals.update({'is_assets_orders': True})
                data = []
                destination = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id),('branch_id', '=', self.env.user.branch_id.id)], order="id", limit=1)
                order_id = self.env['purchase.order'].with_context(context).create(vals)
                if destination:
                    destination = destination.id
                for record in rec.product_ids:
                    data.append((0,0, {
                        'product_id' : record.id,
                        'date_planned': datetime.now(),
                        'destination_warehouse_id': destination or False
                    }))
                order_id.write({'order_line': data})
                order_id.set_analytic_group()
                new_order_id.append(order_id.id)
                for line in order_id.order_line:
                    line._onchange_quantity()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requests for Quotation'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', new_order_id)],
        }
