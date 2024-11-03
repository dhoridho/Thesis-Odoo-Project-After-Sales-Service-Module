# -*- coding: utf-8 -*-

from ast import literal_eval
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def get_table_draft_orders(self, table_id):
        return []

    @api.model
    def _process_order(self, order, draft, existing_order):
        res = super(PosOrder, self)._process_order(order, draft, existing_order)
        if res:
            order = self.env['pos.order'].search([('id','=', res)])
            if order and order.employeemeal_employee_id and order.state in ['paid']:
                order.create_employee_meal_history()
            
            order.create_line_details()
        return res
        
    def create_employee_meal_history(self):
        for order in self:
            budget_amount = 0
            for pay in order.payment_ids:
                if pay.payment_method_id.name.lower() == 'employee budget':
                    budget_amount+=pay.amount
            if budget_amount:
                values = {
                    'order_date': order.date_order,
                    'employee_id': order.employeemeal_employee_id and order.employeemeal_employee_id.id or False,
                    'order_id': order.id,
                    'order_value': budget_amount,
                    'cashier_id': order.cashier_id and order.cashier_id.id or False,
                    'config_id': order.config_id and order.config_id.id or False,
                    'session_id': order.session_id and order.session_id.id or False,
                }
                self.env['pos.employee.meal.history'].create(values)

    def get_table_reservation_popup_data(self):
        customer_ids = self.env['res.partner'].search_read([], ['id', 'name'])
        table_ids = self.env['restaurant.table'].search_read([], ['id', 'name', 'floor_id'])
        floor_ids = self.env['restaurant.floor'].search_read([], ['id', 'name'])
        return {
            'customer': customer_ids,
            'tables': table_ids,
            'floors': floor_ids,
        }

    def has_line_details(self):
        has_line_details = False
        for line in self.lines:
            if line.bom_components:
                has_line_details = True
                break
            if line.pos_combo_options:
                has_line_details = True
                break
        return has_line_details

    def void_order_create_line_details(self):
        self.create_line_details(is_void=True)
        return super(PosOrder, self).void_order_create_line_details()
        
    def create_line_details(self, is_void=False):
        # if not self.has_line_details():
        #     return False

        MrpBomLine = self.env['mrp.bom.line']
        PosComboOption = self.env['mrp.bom.line']
        details = []
        for line in self.lines:
            if line.bom_components:
                domain = [('id','in', [x['id'] for x in literal_eval(line.bom_components) if x.get('checked') == True] )]
                for com in MrpBomLine.search_read(domain, ['product_id','product_qty','is_extra','additional_cost','product_uom_id']):
                    detail = {
                        'product_id': line.product_id.id,
                        'product_component_id': com['product_id'][0],
                        'is_extra': com['is_extra'],
                        'quantity': com['product_qty'] * abs(line.qty),
                        'product_uom_id': com['product_uom_id'][0],
                        'pos_order_line_id': line.id,
                    }
                    if com['is_extra']:
                        detail['price'] = com['additional_cost']

                    details += [(0, 0, detail)]

            if line.pos_combo_options:
                for option in literal_eval(line.pos_combo_options):
                    if option.get('bom_components'): # If Options is BoM Product
                        domain = [('id','in', [x['id'] for x in option['bom_components'] if x.get('checked') == True] )]
                        for com in MrpBomLine.search_read(domain, ['product_id','product_qty','is_extra','additional_cost','product_uom_id']):
                            detail = {
                                'product_id': option['product_id'][0],
                                'product_component_id': com['product_id'][0],
                                'is_extra': com['is_extra'],
                                'quantity': com['product_qty'] * abs(line.qty),
                                'product_uom_id': com['product_uom_id'][0],
                                'pos_order_line_id': line.id,
                            }
                            if com['is_extra']:
                                detail['price'] = com['additional_cost']

                            details += [(0, 0, detail)]

                    else:
                        detail = {
                            'product_id': option['product_id'][0],
                            'quantity': abs(line.qty),
                            'price': option['extra_price'],
                            'product_uom_id': line.product_uom_id.id,
                            'pos_order_line_id': line.id,
                        }
                        if option['extra_price']:
                            detail['price'] = option['extra_price']

                        details += [(0, 0, detail)]

            if not line.bom_components and not line.pos_combo_options:
                if line.product_id.type in ['product']:
                    detail = {
                        'product_id': line.product_id.id,
                        'product_component_id': False,
                        'is_extra': 0,
                        'price': 0,
                        'quantity': abs(line.qty),
                        'product_uom_id': line.product_uom_id.id,
                        'pos_order_line_id': line.id,
                    }
                    details += [(0, 0, detail)]
        
        if details:
            self.write({ 'line_details_ids': details })

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'


