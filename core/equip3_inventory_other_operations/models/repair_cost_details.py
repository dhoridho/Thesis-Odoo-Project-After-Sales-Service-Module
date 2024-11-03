# -*- coding: utf-8 -*-

import json

from odoo import api, models, _
from odoo.tools import float_round

class ReportRepairCost(models.AbstractModel):
    _name = 'report.equip3_inventory_other_operations.report_cost'
    _description = 'Repair Cost Details Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        return {
            'doc_ids': docids,
            'doc_model': 'repair.order',
            'docs': docs,
        }

    @api.model
    def get_html(self, order_id=False, searchQty=1):
        res = self._get_report_data(order_id=order_id, searchQty=searchQty)
        res['lines'] = self.env.ref('equip3_inventory_other_operations.report_cost_details_document')._render({'data': res['lines']})
        return res


    @api.model
    def _get_report_data(self, order_id, searchQty=0):
        lines = {}
        context = dict(self.env.context) or {}
        order_id = self.env['repair.order'].browse(context.get('active_id'))
        lines = self._get_lines()
        vals = {
            'lines': lines,
            'reference': order_id.name,
            'product': order_id.product_id.display_name,
            'product_qty': order_id.product_qty,
            'total': order_id.amount_total,
            'currency': order_id.company_id.currency_id,
        }
        return {
            'lines': vals
        }

    def _get_lines(self):
        context = dict(self.env.context) or {}
        order_id = self.env['repair.order'].browse(context.get('active_id'))
        lines = []
        for line in order_id.operations:
            lines.append({
                'product_id': line.product_id.display_name,
                'product_uom_qty': line.product_uom_qty,
                'price_subtotal': line.price_subtotal,
            })
        return lines