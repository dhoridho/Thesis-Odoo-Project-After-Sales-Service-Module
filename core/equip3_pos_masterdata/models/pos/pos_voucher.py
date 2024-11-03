# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosVoucher(models.Model):
    _name = "pos.voucher"
    _rec_name = 'code'
    _order = 'end_date'
    _description = "Management POS voucher"
    
    active = fields.Boolean('Active', default=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    code = fields.Char('Ean13')
    start_date = fields.Datetime('Start Date', required=1, default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime('Expired Date', required=1,
                               default=lambda self: fields.Datetime.now() + relativedelta(days=365))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('used', 'Used'),
        ('removed', 'Removed')
    ], string='State', default='draft')
    value = fields.Float('Amount')
    apply_type = fields.Selection([
        ('fixed_amount', 'Fixed amount'),
        ('percent', 'Percent (%)'),
    ], string='Apply', default='fixed_amount')
    method = fields.Selection([
        ('general', 'General'),
        ('special_customer', 'Special Customer'),
    ], string='Method', default='general')
    use_date = fields.Datetime('Use Date')
    user_id = fields.Many2one('res.users', 'Create User', readonly=1)
    source = fields.Char('Source Document')
    pos_order_id = fields.Many2one('pos.order', 'Order', readonly=1)
    pos_order_line_id = fields.Many2one('pos.order.line', 'Order Line', readonly=1)
    use_history_ids = fields.One2many('pos.voucher.use.history', 'voucher_id', string='Histories Used', readonly=1)
    number = fields.Char('Number')
    maximum_discount_amount = fields.Float("Maximum Discount Amount", default=0.0)
    minimum_purchase_amount = fields.Float("Minimum Purchase Amount", default=0.0)

    is_generate_voucher = fields.Boolean("Is Generate Voucher", default=False)
    # no_of_usage = fields.Integer('No Of Usage')
    generated_source_id = fields.Many2one('generate.pos.voucher','Source Document')

    limit_restrict_product_ids = fields.Many2many('product.product', string='Multi Products')
    pos_category_ids = fields.Many2many('pos.category', string="Limit PoS Categories")
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    receipt_template_id = fields.Many2one('pos.receipt.template','Receipt Template',domain="[('company_id', '=', company_id)]") 
    source_document_id = fields.Many2one('generate.pos.voucher','Source Document',domain="[('company_id', '=', company_id)]")

    is_customize_sequence = fields.Boolean('Customize Sequence')
    sequence_generate_method = fields.Selection([
        ('Running Number','Running Number'),
        ('Manual Input','Manual Input'),
        ('EAN13','EAN13'),
    ], string='Sequence Generate Method', help='If voucher sequence generate method = EAN13, then automatically generate')
    manual_input_sequence = fields.Char('Manual Input Sequence')
    running_number_prefix = fields.Char('Running Number Prefix')
    running_number_digit = fields.Integer('Running Number Digit')
    brand_ids = fields.Many2many(
        'product.brand',
        'pos_voucher_product_brand_rel',
        'voucher_id',
        'brand_id',
        string='Selected Brand'
    )

    def import_voucher(self, vals):
        vouchers_existing = self.search([
            '|',
            ('code', '=', vals.get('code')),
            ('number', '=', vals.get('number'))
        ])
        if vouchers_existing:
            vouchers_existing.write(vals)
        else:
            self.create(vals)
        return True

    def set_active(self):
        return self.write({'state': 'active'})

    def set_cancel(self):
        return self.write({'state': 'removed'})

    def create_from_ui(self, voucher_vals):
        today = datetime.today()
        end_date = today + timedelta(days=int(voucher_vals['period_days']))
        new_voucher = self.create({
            'number': voucher_vals.get('number'),
            'apply_type': voucher_vals.get('apply_type'),
            'method': voucher_vals.get('method'),
            'value': voucher_vals.get('value'),
            'state': voucher_vals.get('state'),
            'start_date': today,
            'end_date': end_date,
            'user_id': self.env.user.id
        })
        return {
            'number': new_voucher.number,
            'code': new_voucher.code,
            'partner_name': new_voucher.customer_id.name if new_voucher.customer_id else '',
            'method': new_voucher.method,
            'apply_type': new_voucher.apply_type,
            'value': new_voucher.value,
            'start_date': new_voucher.start_date,
            'end_date': new_voucher.end_date,
            'id': new_voucher.id,
        }

    def get_vouchers_by_order_ids(self, order_ids):
        vouchers_data = []
        orders = self.env['pos.order'].sudo().browse(order_ids)
        for order in orders:
            line_ids = [line.id for line in order.lines]
            vouchers = self.sudo().search([('pos_order_line_id', 'in', line_ids)])
            for voucher in vouchers:
                vouchers_data.append({
                    'number': voucher.number,
                    'code': voucher.code,
                    'partner_name': voucher.customer_id.name if voucher.customer_id else '',
                    'method': voucher.method,
                    'apply_type': voucher.apply_type,
                    'value': voucher.value,
                    'start_date': voucher.start_date,
                    'end_date': voucher.end_date,
                    'id': voucher.id,
                })
        return vouchers_data

    @api.model
    def create(self, vals):
        voucher = super(PosVoucher, self).create(vals)

        code = voucher.randomEan13()
        new_vals = {
            'code': code,
            'number': code
        }
        if voucher.is_customize_sequence:
            method = voucher.sequence_generate_method
            if method == 'EAN13':
                new_vals['number'] = code
            if method == 'Manual Input':
                if not vals.get('manual_input_sequence'):
                    raise ValidationError(_('"Manual Input Sequence" is required when sequence generate method: Manual Input'))
                new_vals['number'] = str(vals['manual_input_sequence']).strip().replace(' ','')
            if method == 'Running Number':
                running_number_sequence = voucher._get_running_number_sequence(voucher.generated_source_id.running_number_current_sequence)
                new_vals['number'] = running_number_sequence['sequence']
                voucher.generated_source_id.write({'running_number_current_sequence': running_number_sequence['next_sequence']})
 
        voucher.write(new_vals) 
        _logger.info('NEW VOUCHER: %s' % voucher.number)
        return voucher

    def _get_running_number_sequence(self,current_sequence):
        self.ensure_one()
        prefix = self.running_number_prefix
        suffix = ''
        digits = self.running_number_digit

        next_sequence = int(current_sequence) + 1
        if current_sequence and (isinstance(current_sequence, int) or isinstance(current_sequence, float)):
            current_sequence = str(int(current_sequence)).zfill(digits)
        if next_sequence and (isinstance(next_sequence, int) or isinstance(next_sequence, float)):
            next_sequence = str(int(next_sequence)).zfill(digits)

        sequence = [prefix, current_sequence, suffix]
        sequence = ''.join([x for x in sequence if x])

        return {
            'sequence': sequence,
            'next_sequence': next_sequence,
        }

    def randomEan13(self):
        self.ensure_one()
        format_code = "%s%s%s" % ('999', self.id, datetime.now().strftime("%d%m%y%H%M"))
        return self.env['barcode.nomenclature'].sanitize_ean(format_code)

    def remove_voucher(self):
        return self.write({
            'state': 'removed'
        })

    @api.model
    def get_voucher_by_code(self, code, product_ids=[]):
        _logger.info('get voucher code: %s' % code)
        vouchers = self.env['pos.voucher'].search([
            '|',
            ('code', '=', code), ('number', '=', code),
            ('end_date', '>=', fields.Datetime.now()),
            ('state', '=', 'active')
        ])
        if not vouchers:
            return -1


        if vouchers.limit_restrict_product_ids or vouchers.pos_category_ids:
            productObj = self.env['product.product']
            unblock = False

            for product in product_ids:
                product_check = productObj.search([('id', '=', product)])
                if product_check in vouchers.limit_restrict_product_ids or product_check.pos_categ_id in vouchers.pos_category_ids:
                    unblock = True

            if unblock == False:
                return -2
            else:
                return vouchers.read([])[0]
        else:
            return vouchers.read([])[0]


class PosVoucherUseHistory(models.Model):
    _name = "pos.voucher.use.history"
    _description = "Histories use voucher of customer"

    pos_order_id = fields.Many2one('pos.order', string='Order')
    payment_id = fields.Many2one('pos.payment', string='Payment')
    voucher_id = fields.Many2one('pos.voucher', required=1, string='Voucher', ondelete='cascade')
    value = fields.Float('Value Redeem', required=1)
    used_date = fields.Datetime('Used Date', required=1)
    cashier_id = fields.Many2one('res.users', 'Cashier Added')
