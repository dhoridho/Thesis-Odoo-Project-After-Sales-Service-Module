# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    tick = fields.Boolean(string="Select Product")

    def btn_tick_untick(self):
        if self.tick == True:
            self.tick = False
        else:
            self.tick = True


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    po_extract_id = fields.Many2one(
        'purchase.order', string='Extracted From', track_visibility="onchange", readonly=True, copy=False)
    po_split_id = fields.Many2one('purchase.order', string='Splited From',
                                  track_visibility="onchange", readonly=True, copy=False)
    po_extract_count = fields.Integer(
        'Extracted Quotes', compute='_compute_po_extract_count')
    po_split_count = fields.Integer(
        'Splited Quotes', compute='_compute_po_split_count')

    def _compute_po_extract_count(self):
        if self:
            for rec in self:
                rec.po_extract_count = 0
                extract_ids = self.env['purchase.order'].sudo().search(
                    [('po_extract_id', '=', rec.id)])
                if extract_ids:
                    rec.po_extract_count = len(extract_ids.ids)

    def _compute_po_split_count(self):
        if self:
            for rec in self:
                rec.po_split_count = 0
                split_ids = self.env['purchase.order'].sudo().search(
                    [('po_split_id', '=', rec.id)])
                if split_ids:
                    rec.po_split_count = len(split_ids.ids)

    def action_view_extract_quote(self):
        self.ensure_one()
        return{
            'name': "Extracted RFQ's",
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'domain': [('po_extract_id', '=', self.id)],
            'target': 'current'
        }

    def action_view_split_quote(self):
        self.ensure_one()
        return{
            'name': "Splited RFQ's",
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'domain': [('po_split_id', '=', self.id)],
            'target': 'current'
        }

    def action_split(self):

        return{
            'name': 'Split RFQ',
            'res_model': 'sh.split.rfq.wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new'
        }

    def action_extract(self):

        do_unlink = False
        new_purchase_order_id = False
        for line in self.order_line:
            if line.tick:
                do_unlink = True

        if do_unlink:
            new_purchase_order = self.copy()
            new_purchase_order.po_extract_id = self.id
            new_purchase_order_id = new_purchase_order
            for line in new_purchase_order.order_line:
                if not line.tick:
                    line.unlink()
                else:
                    line.tick = False
        for line in self.order_line:
            if line.tick:
                line.tick = False
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

    def action_check(self):
        if self.order_line:
            for line in self.order_line:
                line.tick = True

    def action_uncheck(self):
        if self.order_line:
            for line in self.order_line:
                line.tick = False
