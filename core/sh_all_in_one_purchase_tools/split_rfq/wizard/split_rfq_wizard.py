# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields


class SplitRFQWizard(models.TransientModel):
    _name = 'sh.split.rfq.wizard'
    _description = 'Split RFQ Wizard'

    split_by = fields.Selection(
        [('new', 'New'), ('existing', 'Existing')], default='new', string="Split By", required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Existing RFQ', domain=[
                                        ('state', 'in', ['draft', 'sent'])])

    def action_split(self):
        active_id = self.env.context.get('active_id')
        active_po = self.env['purchase.order'].sudo().browse(active_id)
        if self.split_by == 'existing':
            do_unlink = False
            new_purchase_order_id = False
            for line in self.purchase_order_id.order_line:
                if line.tick:
                    do_unlink = True

            if do_unlink:
                new_purchase_order = self.purchase_order_id.copy()
                new_purchase_order.po_split_id = self.purchase_order_id.id
                new_purchase_order_id = new_purchase_order
                for line in new_purchase_order.order_line:
                    if not line.tick:
                        line.unlink()
                    else:
                        line.tick = False
            for line in self.purchase_order_id.order_line:
                if line.tick:
                    line.unlink()
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

        elif self.split_by == 'new':
            do_unlink = False
            new_purchase_order_id = False
            for line in active_po.order_line:
                if line.tick:
                    do_unlink = True
            if do_unlink:
                new_purchase_order = active_po.copy()
                new_purchase_order.po_split_id = active_po.id
                new_purchase_order_id = new_purchase_order
                for line in new_purchase_order.order_line:
                    if not line.tick:
                        line.unlink()
                    else:
                        line.tick = False
            for line in active_po.order_line:
                if line.tick:
                    line.unlink()
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
