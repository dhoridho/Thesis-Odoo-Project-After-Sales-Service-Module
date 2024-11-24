from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class ServiceClaim(models.Model):
    _name = 'service.claim'
    _description = 'Service Claim for Automotive Parts'

    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', compute='_compute_sale_order', store=True)
    product_id = fields.Many2one('product.product', string='Part', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    order_date = fields.Date(string='Order Date', compute='_compute_order_date', store=True)

    repair_request_date = fields.Date(string='Repair Request Date', default=fields.Date.today)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date', compute='_compute_warranty_expiry', store=True)
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done')],
                             default='draft', string='Status')
    repair_description = fields.Text(string='Repair Description')


    @api.depends('lot_id')
    def _compute_sale_order(self):
        for record in self:
            if record.lot_id:
                stock_move = self.env['stock.move'].search([('lot_ids', 'in', record.lot_id.id)], limit=1)
                if stock_move:
                    record.sale_order_id = stock_move.picking_id.sale_id
                    record.product_id = record.lot_id.product_id
                    record.partner_id = record.sale_order_id.partner_id

    @api.depends('sale_order_id')
    def _compute_order_date(self):
        for record in self:
            if record.sale_order_id:
                record.order_date = record.sale_order_id.date_order

    @api.depends('order_date')
    def _compute_warranty_expiry(self):
        for record in self:
            if record.order_date:
                record.warranty_expiry_date = record.order_date + timedelta(days=90)

    @api.model
    def create(self, vals):
        order_date = vals.get('order_date')
        if order_date and fields.Date.from_string(order_date) + timedelta(days=90) < fields.Date.today():
            raise ValidationError(_('The warranty period has expired.'))
        return super(ServiceClaim, self).create(vals)

    def action_mark_done(self):
        for record in self:
            record.state = 'done'
            template = self.env.ref('service_claim_mod.email_template_service_done')
            if template:
                template.send_mail(record.id, force_send=True)


# class StockProductionLot(models.Model):
#     _inherit = 'stock.production.lot'
#
#     has_sale_order = fields.Boolean(string='Has Sale Order', compute='_compute_has_sale_order', store=True)
#
#     @api.depends('quant_ids')
#     def _compute_has_sale_order(self):
#         for lot in self:
#             sale_orders = self.env['sale.order'].search([('order_line.move_ids.quant_ids.lot_id', '=', lot.id)])
#             lot.has_sale_order = bool(sale_orders)
