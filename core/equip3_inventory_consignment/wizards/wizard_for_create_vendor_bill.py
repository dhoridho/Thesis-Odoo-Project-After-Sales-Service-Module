# -*- coding: utf-8 -*-

import pytz

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class WizardForCreateVendorBill(models.TransientModel):
    _name = 'wizard.for.create.vendor.bill'
    _description = 'Wizard for Create Vendor Bill'

    date_period = fields.Date('Sales Period Until', default=lambda self: fields.Date.context_today(self))


    def process(self):
        date = self.get_date_period()
        datas = self.get_datas(date=date)
        for data in datas:
            domain = ['|', ('svl_line_ids', 'in' , [data['svl_line_id']]), 
                ('consignment_id','=',data['consignment_id']), ('state','=','draft')]
            account_moves = self.env['account.move'].search(domain)

            # TODO: IF not acount_moves, create new vendor bill and commision
            if not account_moves:
                self.create_vendor_bill(data)
                self.create_vendor_bill_commision(data)
            # TODO: IF acount_moves, then update existing vendor bill and commision
            if account_moves:
                self.update_vendor_bill(data, account_moves)
        return datas

    def get_date_period(self):
        return self.date_period

    def get_datas(self, date):
        date_period = datetime.strptime(f'{date} 00:00:00', '%Y-%m-%d %H:%M:%S')
        date_filter = f'{date} 23:59:59' 

        query = '''
            SELECT 
                ca.id as ca_id,
                svll.id as svls_id,
                sol.id as sol_id,
                sol.name,
                abs(svll.quantity),
                sm.product_id,
                sm.product_uom,
                so.currency_id,
                ca.vendor_id,
                ca.date_end,
                so.id,
                sol.price_unit
            FROM stock_valuation_layer_line as svll
            LEFT JOIN stock_valuation_layer as svl ON svl.id = svll.svl_id
            LEFT JOIN stock_valuation_layer as svl_source ON svl_source.id = svll.svl_source_id
            LEFT JOIN consignment_agreement as ca ON ca.id = svl_source.consignment_id
            LEFT JOIN stock_move as sm ON sm.id = svl.stock_move_id
            LEFT JOIN sale_order_line as sol ON sm.sale_line_id = sol.id
            LEFT JOIN sale_order as so ON so.id = sol.order_id
            LEFT JOIN product_product as pp on sm.product_id = pp.id
            LEFT JOIN product_template as pt on pp.product_tmpl_id = pt.id
            WHERE svl_source.consignment_id is not null 
                AND sol.is_billed_consignment is False 
                AND sol.id is not null --igore data from pos.order
                AND pt.is_consignment = True 
                AND so.date_confirm <= '{date_filter}'
            ORDER by svl.id asc
        '''.format(date_filter=date_filter)
        self._cr.execute(query)
        results = self._cr.fetchall()

        currency_ids = list(set([r[7] for r in results]))
        currencies = self.env['res.currency'].browse(currency_ids)
        currency_obj_by_id = { c.id: c for c in currencies}

        datas = []
        for result in results:
            data = {
                'from': 'sales',
                'date_period': date_period,
                'consignment_id': result[0],
                'svl_line_id': result[1],
                'sale_order_line_id': result[2],
                'sale_order_line_name': result[3],
                'svl_line_qty': result[4],
                'product_id': result[5],
                'product_uom_id': result[6],
                'currency_id': result[7],
                'partner_id': result[8],
                'date_end': result[9],
                'sale_order_id' : result[10],
                'price_unit': result[11],
            }
            data['currency'] = currency_obj_by_id[data['currency_id']]
            data['browse'] = self.get_data_browse(data)
            datas.append(data)
        return datas

    def get_data_browse(self, data):
        domain = [ ('consignment_id','=', data['consignment_id']), ('product_id','=', data['product_id']) ]
        consignment_agreement_line = self.env['consignment.agreement.line'].search(domain, limit=1)
        svl_line_id = self.env['stock.valuation.layer.line'].browse(data['svl_line_id'])
        product_id = self.env['product.product'].browse(data['product_id'])
        uom_uom = self.env['uom.uom'].browse(data['product_uom_id'])

        values = {
            'consignment_agreement_line': consignment_agreement_line,
            'svl_line_id': svl_line_id,
            'product_id': product_id,
            'uom_uom': uom_uom,
        }
        return values

    def _prepare_create_vendor_bill_vals(self, data):
        self.ensure_one()
        date = data['date_period']
        consignment_agreement_line = data['browse']['consignment_agreement_line']
        svl_line_ids = data['browse']['svl_line_id']
        product_id = data['browse']['product_id']
        uom_uom = data['browse']['uom_uom']
        vendor_bills = self.env['account.journal'].search(
            [('type', '=', 'purchase'), ('code', '=', 'BILL')], order='id asc', limit=1)
        payment_term_id = consignment_agreement_line.consignment_id.payment_term_id or False
        invoice_date_due = False
        today = fields.Date.context_today(self)
        if payment_term_id:
            invoice_date = payment_term_id.line_ids[0].days
            invoice_date_due = today + timedelta(days=invoice_date)
        else:
            invoice_date_due = today + timedelta(days=3)

        vals = {
            'auto_reverse_date_mode' : 'custom',
            'date': date,
            'journal_id': vendor_bills.id,
            'currency_id': consignment_agreement_line.consignment_id.currency_id,
            'move_type': 'in_invoice',
            'name': '/',
            'state' : 'draft',
            'invoice_date': date + timedelta(days=3),
            'partner_id' : data['partner_id'],
            'svl_line_id': data['svl_line_id'],
            'svl_line_ids': [(6, 0, svl_line_ids.ids)],
            'consignment_id':data['consignment_id'],
            'branch_id' : consignment_agreement_line.consignment_id.branch_id.id,
            'invoice_date_due': invoice_date_due
        }

        if data['from'] == 'sales':
            sale_order = self.env['sale.order'].browse(data['sale_order_id'])
            sale_order_line = self.env['sale.order.line'].browse(data['sale_order_line_id'])
            vals.update({
                'sale_order_ids': [(6, 0, sale_order.ids)], # ini ada di move pertama di kedua ga ada
                'sale_order_line_ids': [(6, 0, sale_order_line.ids)],
            })

        consigment_price = self.env.company.currency_id._convert(consignment_agreement_line.cost_price, 
            consignment_agreement_line.consignment_id.currency_id, self.env.company, date)
        vals['invoice_line_ids'] = [(0, 0, {
            'product_id': data['product_id'],
            'name': product_id.partner_ref + ' ' + str(data['svl_line_qty']) + ' ' + uom_uom.name,
            'currency_id': consignment_agreement_line.consignment_id.currency_id.id,
            'product_uom_id': data['product_uom_id'],
            'quantity': data['svl_line_qty'],
            'price_unit': consigment_price,
            'account_id': product_id.categ_id.property_account_income_categ_id.id,
            'tax_ids': [(6, 0, product_id.supplier_taxes_id.ids)],
            'price_subtotal': (data['svl_line_qty'] * data['price_unit']),
        })]
        return vals

    def create_vendor_bill(self, data):
        self.ensure_one()
        vals = self._prepare_create_vendor_bill_vals(data)
        move = self.env['account.move'].with_context(check_move_validity=False).create(vals)
        move._compute_amount()

        if data['from'] == 'sales':
            sale_order = self.env['sale.order'].browse(data['sale_order_id'])
            sale_order_line = self.env['sale.order.line'].browse(data['sale_order_line_id'])
            move.write({'sale_order_line_ids': [(4, sale_order_line.id)]})
            sale_order.bill_consignment_ids = [(4, move.id)]
            sale_order_line.write({'is_billed_consignment' : True}) 

        return move

    def _prepare_create_vendor_bill_commision_vals(self, data):
        self.ensure_one()
        date = data['date_period']
        consignment_agreement_line = data['browse']['consignment_agreement_line']
        svl_line_ids = data['browse']['svl_line_id']
        product_id = data['browse']['product_id']
        uom_uom = data['browse']['uom_uom']
        vendor_bills = self.env['account.journal'].search(
            [('type', '=', 'purchase'), ('code', '=', 'BILL')], order='id asc', limit=1)
        
        vals = {
            'auto_reverse_date_mode' : 'custom',
            'date': date,
            'journal_id': vendor_bills.id,
            'currency_id': consignment_agreement_line.consignment_id.currency_id,
            'move_type': 'entry',
            'partner_id' : data['partner_id'],
            'svl_line_id': data['svl_line_id'],
            'svl_line_ids': [(6, 0, svl_line_ids.ids)],
            'consignment_id':data['consignment_id'],
            'branch_id' : consignment_agreement_line.consignment_id.branch_id.id,
            'is_commission' : True
        }

        commision_price = (data['svl_line_qty'] * data['price_unit']) - (data['svl_line_qty'] * consignment_agreement_line.cost_price)
        commision_price = self.env.company.currency_id._convert(commision_price, data['currency'], self.env.company, date)
        vals.update({
            'line_ids': [
                (0, 0, {
                    'name': 'Commission' + ' ' + product_id.partner_ref + ' ' + str(data['svl_line_qty']) + ' ' + uom_uom.name,
                    'product_id': product_id.id,
                    'product_uom_id': uom_uom.id,
                    'currency_id': consignment_agreement_line.consignment_id.currency_id,
                    'quantity': 1,
                    'account_id': product_id.categ_id.consignment_commision_account.id,
                    'debit': 0.0,
                    'credit': abs(commision_price)
                }),
                (0, 0, {
                    'name': 'Commission' + ' ' + product_id.partner_ref + ' ' + str(data['svl_line_qty']) + ' ' + uom_uom.name,
                    'product_id': product_id.id,
                    'product_uom_id': uom_uom.id,
                    'currency_id': consignment_agreement_line.consignment_id.currency_id,
                    'quantity': 1,
                    'account_id': product_id.categ_id.property_account_income_categ_id.id,
                    'debit': abs(commision_price),
                    'credit': 0.0
                }),
            ]
        })

        if data['from'] == 'sales':
            sale_order_line = self.env['sale.order.line'].browse(data['sale_order_line_id'])
            vals.update({
                'sale_order_line_ids': [(6, 0, sale_order_line.ids)],
            })
            
        return vals

    def create_vendor_bill_commision(self, data):
        self.ensure_one()
        vals = self._prepare_create_vendor_bill_commision_vals(data)
        move = self.env['account.move'].with_context(check_move_validity=False).create(vals)
        return move


    def do_update_vendor_bill(self, move, data):
        self.ensure_one()
        date = data['date_period']
        consignment_agreement_line = data['browse']['consignment_agreement_line']
        svl_line_id = data['browse']['svl_line_id']
        product_id = data['browse']['product_id']
        uom_uom = data['browse']['uom_uom']

        amount_last_consigment = -((data['svl_line_qty'] * data['price_unit']) - (data['svl_line_qty'] * consignment_agreement_line.cost_price))
        consigment_price = self.env.company.currency_id._convert(consignment_agreement_line.cost_price, consignment_agreement_line.consignment_id.currency_id, self.env.company, date)
        commision_price = self.env.company.currency_id._convert((data['svl_line_qty'] * data['price_unit']) -(data['svl_line_qty'] * consignment_agreement_line.cost_price), data['currency'], self.env.company, date)
        move_line_same_product = move.line_ids.filtered(lambda x: x.product_id.id == data['product_id'])

        # TODO: If product id already on line, then sum the quantity
        if move_line_same_product:
            new_move_line_product = []
            start_index = len(product_id.partner_ref)
            end_index = move_line_same_product.name.find(uom_uom.name)
            number_string = move_line_same_product.name[start_index:end_index]
            result = float(number_string) if '.' in number_string else int(number_string)
            sum_qty = result + data['svl_line_qty']

            new_move_line_product.append((0, 0, {
                'product_id': data['product_id'],
                'name': product_id.partner_ref + ' ' + str(sum_qty) + ' ' + uom_uom.name,
                'currency_id': data['currency_id'],
                'product_uom_id': data['product_uom_id'],
                'quantity': move_line_same_product.quantity + data['svl_line_qty'],
                'price_unit': consigment_price,
                'account_id': product_id.categ_id.property_account_income_categ_id.id,
                'tax_ids': [(6, 0, product_id.supplier_taxes_id.ids)],
                'price_subtotal': move_line_same_product.price_subtotal + consigment_price
            }))
            move_line_same_product.with_context(check_move_validity=False).unlink()
            move.with_context(check_move_validity=False).write({'invoice_line_ids' : new_move_line_product})
            move._compute_amount()

        # TODO: If product not in line
        else:
            invoice_line_new = []
            invoice_line_new.append((0, 0, {
                'product_id': data['product_id'],
                'name': product_id.partner_ref + ' ' + str(data['svl_line_qty']) + ' ' + uom_uom.name,
                'currency_id': data['currency_id'],
                'product_uom_id': data['product_uom_id'],
                'quantity': data['svl_line_qty'],
                'price_unit': consigment_price,
                'account_id': product_id.categ_id.property_account_income_categ_id.id,
                'tax_ids': [(6, 0, product_id.supplier_taxes_id.ids)],
                'price_subtotal': consigment_price
            }))
            move.with_context(check_move_validity=False).write({'invoice_line_ids' : invoice_line_new})
            move._compute_amount()

        if data['from'] == 'sales':
            sale_order = self.env['sale.order'].browse(data['sale_order_id'])
            sale_order_line = self.env['sale.order.line'].browse(data['sale_order_line_id']) 
            move.write({'sale_order_line_ids': [(4, sale_order_line.id)]})
            sale_order_line.write({'is_billed_consignment' : True})

        move.with_context(check_move_validity=False).write({'svl_line_ids' : [(4, svl_line_id.id)]})
        return move

    def do_update_vendor_bill_commission(self, move, data):
        self.ensure_one()
        date = data['date_period']
        product_id = data['browse']['product_id']
        consignment_agreement_line = data['browse']['consignment_agreement_line']

        commision_price = self.env.company.currency_id._convert((data['svl_line_qty'] * data['price_unit']) -(data['svl_line_qty'] * consignment_agreement_line.cost_price), data['currency'], self.env.company, date)
        credit_line = move.line_ids.filtered(lambda o: o.account_id == product_id.categ_id.consignment_commision_account)
        debit_line = move.line_ids.filtered(lambda o: o.account_id == product_id.categ_id.property_account_income_categ_id)

        move.write({
            'line_ids': [
                (1, credit_line.id, {'credit': credit_line.credit + commision_price, 'amount_currency': credit_line.amount_currency - commision_price}),
                (1, debit_line.id, {'debit': debit_line.debit + commision_price, 'amount_currency': debit_line.amount_currency + commision_price}),
            ]
        })
        return move

    def update_vendor_bill(self, data, account_moves):
        svl_line_id = data['browse']['svl_line_id']
        for move in account_moves:
            if not move.is_commission and (svl_line_id.id not in move.svl_line_ids.ids and move.state == 'draft'):
                # TODO: Update value for vendor bill
                self.do_update_vendor_bill(move, data)
            else:
                # TODO: Update value for vendor bill commission
                self.do_update_vendor_bill_commission(move, data)
        return account_moves