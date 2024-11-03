# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
from datetime import datetime

class WizardForCreateVendorBill(models.TransientModel):
    _inherit = 'wizard.for.create.vendor.bill'

    def get_datas(self, date):
        datas = super(WizardForCreateVendorBill, self).get_datas(date)

        date_period = datetime.strptime(f'{date} 00:00:00', '%Y-%m-%d %H:%M:%S')
        date_filter = f'{date} 23:59:59' 
        query = '''
            SELECT 
                ca.id AS consignment_id, --0
                svll.id AS svl_line_id, --1
                pol.id AS pos_order_line_id, --2
                pol.name AS pos_order_line_name, --3
                abs(svll.quantity) AS svl_line_qty_positive, --4
                sm.product_id, --5
                sm.product_uom AS product_uom_id, --6
                po.currency_id, --7
                ca.vendor_id AS partner_id, --8
                ca.date_end, --9
                po.id AS pos_order_id, --10
                pol.price_unit --11
            FROM stock_valuation_layer_line AS svll
            LEFT JOIN stock_valuation_layer AS svl ON svl.id = svll.svl_id
            LEFT JOIN consignment_agreement AS ca ON ca.id = svl.consignment_id
            LEFT JOIN stock_move AS sm ON sm.id = svl.stock_move_id
            LEFT JOIN pos_order_line AS pol ON sm.pos_order_line_id  = pol.id
            LEFT JOIN pos_order AS po ON po.id = pol.order_id
            LEFT JOIN product_product AS pp on sm.product_id = pp.id
            LEFT JOIN product_template AS pt on pp.product_tmpl_id = pt.id
            WHERE svl.consignment_id IS NOT NULL 
                AND (pol.is_billed_consignment is False OR pol.is_billed_consignment IS NULL)
                AND pt.is_consignment = True 
                AND po.id IS NOT NULL --igore data from sale.order
                AND po.date_order <= '{date_filter}'
            ORDER BY svl.id ASC
        '''.format(date_filter=date_filter)
        self._cr.execute(query)
        results = self._cr.fetchall()

        currency_ids = list(set([r[7] for r in results]))
        currencies = self.env['res.currency'].search([('id','in',currency_ids)])
        currency_obj_by_id = { c.id: c for c in currencies}

        for result in results:
            data = {
                'from': 'pos',
                'date_period': date_period,
                'consignment_id': result[0],
                'svl_line_id': result[1],
                'pos_order_line_id': result[2],
                'pos_order_line_name': result[3],
                'svl_line_qty': result[4],
                'product_id': result[5],
                'product_uom_id': result[6],
                'currency_id': result[7], 
                'partner_id': result[8],
                'date_end': result[9],
                'pos_order_id' : result[10],
                'price_unit': result[11],
            }
            data['currency'] = currency_obj_by_id[data['currency_id']]
            data['browse'] = self.get_data_browse(data)
            datas.append(data)
        return datas


    def _prepare_create_vendor_bill_vals(self, data):
        vals = super(WizardForCreateVendorBill, self)._prepare_create_vendor_bill_vals(data)
        if data['from'] == 'pos':
            pos_order_line = self.env['pos.order.line'].search([('id','=', data['pos_order_line_id'])])
            vals.update({
                'pos_order_line_ids': [(6, 0, pos_order_line.ids)],
            })
        return vals

    def create_vendor_bill(self, data):
        move = super(WizardForCreateVendorBill, self).create_vendor_bill(data) 
        if data['from'] == 'pos':
            pos_order = self.env['pos.order'].search([('id','=', data['pos_order_id'])])
            pos_order_line = self.env['pos.order.line'].search([('id','=', data['pos_order_line_id'])])
            move.write({'pos_order_line_ids': [(4, pos_order_line.id)]})
            pos_order.bill_consignment_ids = [(4, move.id)]
            pos_order_line.write({'is_billed_consignment' : True})
        return move

    def do_update_vendor_bill(self, move, data):
        res = super(WizardForCreateVendorBill, self).do_update_vendor_bill(move, data)
        if data['from'] == 'pos':
            pos_order_line = self.env['pos.order.line'].search([('id','=', data['pos_order_line_id'])])
            move.write({'pos_order_line_ids': [(4, pos_order_line.id)]})
            pos_order_line.write({'is_billed_consignment' : True})
        return res