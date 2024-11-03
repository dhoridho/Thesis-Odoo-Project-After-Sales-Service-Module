# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import float_is_zero


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    pos_order_id = fields.Many2one('pos.order', string='POS Order')
    payment_difference = fields.Float('Payment Difference', compute='_compute_payment_difference', store=True)

    @api.depends('amount')
    def _compute_payment_difference(self):
        for rec in self:
            order = rec.pos_order_id
            difference = 0
            if order:
                difference = order.amount_total - (order.payment_paid + rec.amount)
            rec.payment_difference = difference

    def add_payment(self, data):
        self.env['pos.payment'].create(data)
        order = self.env['pos.order'].browse(data['pos_order_id'])
        currency = order.currency_id
        order.amount_paid = sum(order.payment_ids.mapped('amount'))
        if float_is_zero(order.amount_total - order.amount_paid, precision_rounding=currency.rounding):
            order.action_pos_order_paid()
        return order.id

    @api.model
    def default_get(self, default_fields):
        vals = super(PosMakePayment, self).default_get(default_fields)

        active_id = self._context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            vals['pos_order_id'] = order.id
            if order.is_payment_method_with_receivable:
                vals['amount'] = order.amount_total - (order.payment_paid)
        return vals


    def check(self):
        self.ensure_one()
        order = self.env['pos.order'].browse(self.env.context.get('active_id', False))
        
        if order.return_order_id:
            order.return_order_id.write({
                'return_status': order.return_order_id.return_order_state
            })

        if order.is_payment_method_with_receivable:
            init_data = self.read()[0]
            values = {
                'amount': init_data['amount'],
                'payment_name': init_data['payment_name'],
                'payment_method_id': init_data['payment_method_id'][0]
            }
            return self.action_pay_receivable(order, values, is_window_close=True)
        return super(PosMakePayment, self).check()


    def action_pay_receivable(self, order, values, is_window_close=False):
        currency = order.currency_id
        if not float_is_zero(values['amount'], precision_rounding=currency.rounding):
            values = {
                'pos_order_id': order.id,
                'amount': order._get_rounded_amount(values['amount']),
                'name': values['payment_name'],
                'payment_method_id': values['payment_method_id'],
            }
            order.add_payment(values)

        payment_paid = order.payment_paid
        if values.get('is_from_frontend') == True:
            payment_paid = order.payment_paid + values['amount']

        if payment_paid < order.amount_total:
            order.write({ 'state': 'partially paid' })
        else:
            order.write({ 'state': 'done' })
            order.write({ 'amount_paid': payment_paid })

            if order.session_id.state != 'closed': # IF Session is not Closed
                order.action_pos_order_paid()
                order._create_order_picking()
                domain = [('state','=', 'draft'), ('pos_order_id','=', order.id)]
                moves = self.env['account.move'].search(domain)
                moves.action_post()

        if order.partner_id:
            order.partner_id._compute_customer_credit_limit()
        
        if is_window_close:
            return {'type': 'ir.actions.act_window_close'}
        return order


    def action_pay_receivable_frontend(self, values):
        order = self.env['pos.order'].browse(values['pos_order_id'])
        payment_method = self.env['pos.payment.method'].browse(values['payment_method_id'])
        if order.is_payment_method_with_receivable and order.state in ['invoiced','partially paid']:
            amount = values['amount']
            values = {
                'amount': amount,
                'payment_name': payment_method.name,
                'payment_method_id': payment_method.id,
                'is_from_frontend': True
            }

            difference = order.amount_total - (order.payment_paid + amount)
            if difference < 0:
                values['amount'] = order.amount_total - order.payment_paid
            self.action_pay_receivable(order, values)
        return {'status': 'success'}

    def action_multipay_receivable_frontend(self, vals):
        order = self.env['pos.order'].browse(vals['pos_order_id'])
        if order.state in ['invoiced','partially paid']:
            payments = vals['payments']
            for payment in payments:
                amount = payment['amount']
                payment_method = self.env['pos.payment.method'].browse(payment['id'])
                currency = order.currency_id
                if not float_is_zero(amount, precision_rounding=currency.rounding):
                    values = {
                        'pos_order_id': order.id,
                        'amount': order._get_rounded_amount(amount),
                        'name': payment_method.name,
                        'payment_method_id': payment_method.id,
                    }
                    if order.session_id.state == 'closed': # IF Session is Closed
                        reference = 'Pay Receivable from another session'
                        if vals.get('pos_session_id'):
                            pos_session = self.env['pos.session'].sudo().browse(vals['pos_session_id'])
                            if pos_session:
                                reference += '.%s(ID:%s)' % (pos_session.name, pos_session.id)
                        values['ref'] = reference

                    order.add_payment(values)

            payment_paid = order.payment_paid
            if payment_paid < order.amount_total:
                order.write({ 'state': 'partially paid' })
            else:
                order.write({ 'state': 'done' })
                order.write({ 'amount_paid': payment_paid })

                if order.session_id.state != 'closed': # IF Session is not Closed
                    order.action_pos_order_paid()
                    order._create_order_picking()
                    domain = [('state','=', 'draft'), ('pos_order_id','=', order.id)]
                    moves = self.env['account.move'].search(domain)
                    moves.action_post()

            if order.partner_id:
                order.partner_id._compute_customer_credit_limit()

        field_list = self.env['pos.cache.database'].get_fields_by_model('pos.order')
        field_list += ['payment_paid']
        data_order = self.env['pos.order'].search_read([('id','=', order.id)], field_list)[0]

        field_list = ['payment_date', 'pos_order_id', 'amount', 'payment_method_id', 'name']
        payments = self.env['pos.payment'].sudo().search_read([('pos_order_id','=', order.id)], field_list)
        
        return { 'status': 'success', 'data_order': data_order, 'payments': payments }

