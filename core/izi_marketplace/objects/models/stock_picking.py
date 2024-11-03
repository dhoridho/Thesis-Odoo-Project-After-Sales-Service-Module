# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    mp_account_id = fields.Many2one('mp.account', string="Marketplace Account", readonly=True,
                                   related="sale_id.mp_account_id", store=True)
    marketplace = fields.Selection(string="Marketplace", readonly=True,
                                   related="sale_id.mp_account_id.marketplace", store=True)
    mp_order_status = fields.Selection(string="MP Order Status", related="sale_id.mp_order_status", required=False,
                                       store=True)
    mp_delivery_type = fields.Selection(
        string="MP Delivery Type", related="sale_id.mp_delivery_type", store=True)
    
    mp_delivery_carrier_name = fields.Char(
        string="MP Delivery Name", related="sale_id.mp_delivery_carrier_name", store=True)

    mp_awb_number = fields.Char(
        string="MP AWB Number", related="sale_id.mp_awb_number", store=True)

    mp_invoice_number = fields.Char(
        string="MP Invoice Number", related="sale_id.mp_invoice_number", store=True)
    mp_package_id = fields.Char(string="MP Package ID", related="sale_id.mp_package_id", store=True)
    is_preorder = fields.Boolean(
        string="Is Preorder", related="sale_id.is_preorder", store=True)

    def write(self, vals):
        for pick in self:
            if not pick.picking_type_code:
                vals['picking_type_code'] = pick.picking_type_id.code
        res = super(StockPicking, self).write(vals)
        return res

    def do_print_label(self):
        for picking in self:
            if picking.mp_account_id.auto_print_label:
                return picking.get_label()
        return False

    def get_label(self):
        marketplace = self.mapped('marketplace')
        mp_account_ids = self.mapped('sale_id.mp_account_id.id')
        if marketplace.count(marketplace[0]) == len(marketplace):
            if mp_account_ids.count(mp_account_ids[0]) == len(mp_account_ids):
                if hasattr(self, '%s_print_label' % marketplace[0]):
                    return getattr(self, '%s_print_label' % marketplace[0])()
            else:
                raise ValidationError('Please select the same marketplace account.')
        else:
            raise ValidationError('Please select the same marketplace channel.')

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            if picking.state == 'done' and picking.sale_id and picking.picking_type_id.code == 'outgoing' and picking.mp_account_id and picking.mp_account_id.create_invoice_after_delivery:
                so = picking.sale_id
                if so.invoice_status in ['no', 'to invoice']:
                    so._create_invoices(final=True)
                    for move in so.invoice_ids:
                        if move.state == 'draft':
                            move.action_post()
        return res

    def action_download_shipping_label(self):
        print('Stock Picking: Download Shipping Label')
        marketplace = self.mapped('marketplace')
        mp_account_ids = self.mapped('sale_id.mp_account_id.id')
        if marketplace.count(marketplace[0]) == len(marketplace):
            if mp_account_ids.count(mp_account_ids[0]) == len(mp_account_ids):
                if hasattr(self, '%s_download_shipping_label' % marketplace[0]):
                    return getattr(self, '%s_download_shipping_label' % marketplace[0])()
            else:
                raise ValidationError('Please select the same marketplace account.')
        else:
            raise ValidationError('Please select the same marketplace channel.')

    def button_action_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            if record.sudo().mapped('move_ids_without_package'):
                record.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                record.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
        return True