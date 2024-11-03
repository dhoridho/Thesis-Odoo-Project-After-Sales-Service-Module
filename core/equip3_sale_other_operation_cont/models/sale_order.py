from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for record in self:
            if record.state in ('sale', 'cancel'):
                for line in record.order_line:
                    if line.bo_id:
                        qty = 0
                        bo_line = self.env['orderline.orderline'].browse(line.bo_id)
                        all = self.env['sale.order.line'].search([('bo_id', '=', line.bo_id),('order_id.state', '=', 'sale')])
                        for rec in all:
                            qty += rec.product_uom_qty
                        # bo_line.ordered_qty = qty
                        # bo_line.remaining_quantity = bo_line.quantity - bo_line.ordered_qty
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        blanket_obj = self.env['saleblanket.saleblanket'].search([('name', '=', self.origin)])
        if self.origin and 'BO' in self.origin:
            for record in self:
                for line in record.order_line:
                    qty = line.product_uom_qty
                    product_id = line.product_template_id.id
                    for bo in blanket_obj.order_line_ids:
                        bo_product_id = bo.product_id.product_tmpl_id.id
                        bo_qty = bo.quantity
                        if product_id == bo_product_id:
                            bo.ordered_qty = bo.ordered_qty - qty
                            bo.remaining_quantity = bo.quantity - bo.ordered_qty
        return res


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    bo_id = fields.Integer('BO id')
    
    @api.constrains('qty_delivered')
    def set_delivered_bo(self):
        for res in self:
            if res.bo_id:
                qty = 0
                bo_line = self.env['orderline.orderline'].browse(res.bo_id)
                all = self.env['sale.order.line'].search([('bo_id', '=', res.bo_id)])
                for rec in all:
                    qty += rec.qty_delivered
                bo_line.delivered_qty = qty

class AccountMove(models.Model):
    _inherit = 'account.move'


    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for record in self:
            order_id = record.invoice_line_ids.mapped('sale_line_ids.order_id')
            if record.state in ('draft', 'posted', 'cancel') and order_id:
                for line in order_id.order_line:
                    if line.bo_id:
                        qty = 0
                        bo_line = self.env['orderline.orderline'].browse(line.bo_id)
                        all = self.env['sale.order.line'].search([('bo_id', '=', line.bo_id),('order_id.state', '=', 'sale')])
                        filter_move_lines = all.mapped('invoice_lines').filtered(lambda r:r.move_id.state == 'posted')
                        # bo_line.qty_invoiced = sum(filter_move_lines.mapped('quantity'))
        return res
