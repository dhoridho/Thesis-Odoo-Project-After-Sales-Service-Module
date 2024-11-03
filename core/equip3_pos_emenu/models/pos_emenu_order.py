# -*- coding: utf-8 -*-

import copy

from datetime import datetime
from odoo import api, fields, models, _

def format_currency(currency, amount):
    amount = '{:20,.2f}'.format(amount)
    if (currency.position == 'after'):
        return str(amount) + ' ' + (currency.symbol or '');
    else:
        return (currency.symbol or '') + ' ' + str(amount);

class PosEmenuOrder(models.Model):
    _name = 'pos.emenu.order'
    _description = 'POS E-Menu Order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    date = fields.Datetime('Order Date')
    state = fields.Selection(
        [('cancelled','Cancelled'),('created','Created'),('new_order','New Order'),
        ('received','Received'),('to_pay','To Pay'),('paid','Paid')], 
        string='Status', default='draft', tracking=True, 
        help='''- Created: QR Code printed 
                - New Order: New order received
                - Received: Order served to the Customer
                - To Pay: Customer click Payment in the app''')
    line_ids = fields.One2many('pos.emenu.order.line','order_id', string='Lines (all)')
    order_session_uid = fields.Char('Order Session UID')
    pos_session_id = fields.Many2one('pos.session', 'Session')
    pos_config_id = fields.Many2one('pos.config', 'Point of Sale')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', compute='_compute_pricelist_id')
    table_id = fields.Many2one('restaurant.table', 'Table')
    floor_id = fields.Many2one('restaurant.floor', 'Floor')
    pos_order_id = fields.Many2one('pos.order', 'POS Order')
    amount_total = fields.Float('Total', compute='_compute_amount_total')
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id')
    next_order_number = fields.Integer('Next Order Number', compute='_compute_next_order_number')
    order_count = fields.Integer('Order Count', compute='_compute_order_count')
    branch_id = fields.Many2one('res.branch', string='Branch', related="pos_session_id.pos_branch_id")
    company_id = fields.Many2one('res.company', string='Company', related="pos_session_id.company_id")


    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pos.emenu.order') or _('New')

        return super(PosEmenuOrder, self).create(vals)

    def _compute_amount_total(self):
        for rec in self:
            amount_total = 0
            if self._context.get('ctx_state') == 'created':
                amount_total = sum([ l.subtotal_incl for l in rec.line_ids if l.state == 'created'])
            else:
                amount_total = sum([ l.subtotal_incl for l in rec.line_ids])
            rec.amount_total = amount_total

    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.pos_session_id.currency_id

    def _compute_pricelist_id(self):
        for rec in self:
            rec.pricelist_id = rec.pos_config_id.pricelist_id

    def action_create(self, vals):
        PosEmenuOrder = self.env[self._name]

        order_values = {
            'order_session_uid': vals['order_session_uid'],
            'pos_session_id': vals['pos_session_id'],
            'pos_config_id': vals['pos_config_id'],
            'table_id': vals['table_id'],
            'floor_id': vals['floor_id'],
            'date': fields.Datetime.now(),
            'state': 'created',
        }
        domain = [('order_session_uid','=', vals['order_session_uid'])]
        emenu_order = PosEmenuOrder.search(domain)
        if not emenu_order:
            emenu_order = PosEmenuOrder.create(order_values)

        resp = {
            'status': 'success',
            'printed_date': emenu_order.date,
            'emenu_order_id': emenu_order.id,
            'emenu_url': emenu_order.get_emenu_url(),
        }
        return resp

    def get_emenu_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url.pos_emenu')
        if not base_url:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        access = 'EM'
        access += f'.{self.pos_session_id.id}' + datetime.now().strftime(':%d') 
        access += f'.{self.pos_config_id.id}' + datetime.now().strftime(':%S') 
        access += f'.{self.id}' + datetime.now().strftime(':%M') 
        access += f'.{self.table_id.id}' + datetime.now().strftime(':%m') 
        access += f'.{self.floor_id.id}' + datetime.now().strftime(':%d')
        return base_url + f'/emenu/redirect/{access}'

    def _compute_next_order_number(self):
        for rec in self:
            order_numbers = [l.order_number for l in rec.line_ids]
            rec.next_order_number = order_numbers and max(list(set(sorted(order_numbers)))) + 1 or 1

    def _compute_order_count(self):
        for rec in self:
            order_numbers = [l.order_number for l in rec.line_ids]
            rec.order_count = len(list(set(sorted(order_numbers))))

    def action_validate(self):
        self.ensure_one()
        self.write({ 'state': 'received' })
        line_ids = self.line_ids.filtered(lambda r: r.state == 'new_order')
        for line in line_ids: 
            line.write({ 'state': 'received' })
        return { 'status': 'success' }

    def action_save_cashier_changes(self, vals):
        ProductProduct = self.env['product.product'].with_context(_emenu_pricelist=self.pricelist_id)
        for line in vals['lines']:
            product = ProductProduct.browse(line['product_id'])
            tax_ids = []
            for tax in product.product_tmpl_id.taxes_id:
                tax_ids += [(4, tax.id)]

            value = copy.deepcopy(line)
            value.update({
                'created_from': 'pos',
                'order_id': self.id,
                'order_number': self.next_order_number,
                'price': product.emenu_price,
                'tax_ids': tax_ids,
                'state': 'received',
            })

            self.env['pos.emenu.order.line'].create(value)

        return { 'status': 'success' }

    def sync_emenu_orders(self, vals):
        PosEmenuOrderLine = self.env[self._name + '.line'].sudo()
        values = []

        order_uids = vals.get('order_uids')
        if order_uids:
            order_fields = ['id','write_date','state','date','order_session_uid','line_ids']
            domain = [('state','in',['new_order']), ('order_session_uid','in', order_uids)]
            orders = self.env[self._name].sudo().search_read(domain, order_fields)

            order_line_fields = ['id','write_date','order_id','product_id','qty','price','note', 'order_number','state']
            domain = [('order_id.state','in',['new_order']), ('order_id.order_session_uid','in', order_uids)]
            lines = PosEmenuOrderLine.search_read(domain, order_line_fields)
            lines_by_order_id = {}
            for line in lines:
                order_id = line['order_id'][0]
                if order_id not in lines_by_order_id:
                    lines_by_order_id[order_id] = [line]
                else:
                    lines_by_order_id[order_id] += [line]

            for order in orders:
                data = copy.deepcopy(order)
                data['lines'] = lines_by_order_id[order['id']]
                values += [data]
            

        return values
        
    def sync_emenu_order(self):
        self.ensure_one()
        PosEmenuOrderLine = self.env[self._name + '.line'].sudo()
        order_fields = ['id','write_date','state','date']
        order = self.env[self._name].sudo().search_read([('id','=', self.id)], order_fields)[0]

        order_line_fields = ['id','write_date','product_id','qty','price','note', 'order_number','state']
        lines = PosEmenuOrderLine.search_read([('id','in', self.line_ids.ids), ('state','in', ['new_order'])], order_line_fields)
        
        return { 
            'order': order,
            'lines': lines,
        }
    
    def format_currency(self, currency, amount):
        return format_currency(currency, amount)

class PosEmenuOrderLine(models.Model):
    _name = 'pos.emenu.order.line'
    _description = 'POS E-Menu Order Line'
    _order = 'order_number asc'

    order_id = fields.Many2one('pos.emenu.order', 'Order')
    order_number = fields.Integer('Order Number')
    product_id = fields.Many2one('product.product', 'Product') 
    qty = fields.Integer('Quantity')
    price = fields.Float('Price')
    discount = fields.Float('Price')
    tax_ids = fields.Many2many(
        'account.tax', 
        'pos_emenu_order_line_account_tax_rel', 
        'line_id', 
        'tax_id', 
        string='Taxes')
    note = fields.Char('Note')
    state = fields.Selection(
        [('created','Created'),('new_order','New Order'),('received','Received'),('to_pay','To Pay')], 
        string='Status', default='draft', help='''
                - Created: QR Code printed 
                - New Order: New order received
                - Received: Order served to the Customer
                - To Pay: Customer click Payment in the app''')
    created_from = fields.Selection([('pos','POS'),('emenu','E-Menu')], string='Created From')
    order_type = fields.Selection([('dine-in','Dine In'),('takeaway','Take Away')], string='Order Type')
    subtotal = fields.Float('Subtotal w/o Tax', digits=0, compute='_compute_amount_line_all', store=False)
    subtotal_incl = fields.Float('Subtotal', digits=0, compute='_compute_amount_line_all', store=False)

    @api.depends('product_id','qty','discount','tax_ids')
    def _compute_amount_line_all(self):
        for rec in self:
            partner = False
            tax_ids_after_fiscal_position = self.env['account.fiscal.position'].map_tax(rec.tax_ids, rec.product_id, partner)
            price = rec.price * (1 - (rec.discount or 0.0) / 100.0)
            taxes = tax_ids_after_fiscal_position._emenu_compute_all(price, rec.order_id.pricelist_id.currency_id, rec.qty, product=rec.product_id, partner=partner)
            rec.subtotal_incl = taxes['total_included']
            rec.subtotal = taxes['total_excluded']