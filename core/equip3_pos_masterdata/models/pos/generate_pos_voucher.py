# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

class GeneratePosVoucher(models.Model):
    _name = "generate.pos.voucher"
    _order = "id desc"
    _description = "Generate POS voucher"

    customer_id = fields.Many2one('res.partner', string='Customer')
    code = fields.Char('Ean13')
    start_date = fields.Datetime('Start Date', required=1, default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime('Expired Date', required=1,
                               default=lambda self: fields.Datetime.now() + relativedelta(days=365))
    maximum_discount_amount = fields.Float("Maximum Discount Amount", default=0.0)
    minimum_purchase_amount = fields.Float("Minimum Purchase Amount", default=0.0,help="The minimum purchase amount required for the voucher to be used. if 0 = can always be used")
    limit_restrict_product_ids = fields.Many2many('product.product', string='Multi Products')
    pos_category_ids = fields.Many2many('pos.category', string="Limit PoS Categories")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('used', 'Used'),
        ('removed', 'Removed')
    ], string='State', default='active')
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
    use_history_ids = fields.One2many('generate.pos.voucher.use.history', 'voucher_id', string='Histories Used', readonly=1)
    name = fields.Char(string='Reference')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    no_of_usage = fields.Integer("No Of Usage", default=0,help="Number of vouchers that can be generated. If 0 = Unlimited.")
    no_of_used = fields.Integer("No Of Used", compute='_compute_get_no_of_used')
    minimum_spend = fields.Float('Minimum Spend',help="The minimum purchase amount required for the voucher to be generated. if 0 = always generate voucher")

    is_customize_sequence = fields.Boolean('Customize Sequence')
    sequence_generate_method = fields.Selection([
        ('Running Number','Running Number'),
        ('Manual Input','Manual Input'),
        ('EAN13','EAN13'),
    ], string='Sequence Generate Method', help='If voucher sequence generate method = EAN13, then automatically generate')
    manual_input_sequence = fields.Char('Manual Input Sequence')
    running_number_prefix = fields.Char('Running Number Prefix')
    running_number_digit = fields.Integer('Running Number Digit', default=3)
    running_number_current_sequence = fields.Char('Running Number Current Sequence', default='001')
    brand_ids = fields.Many2many(
        'product.brand',
        'generate_pos_voucher_product_brand_rel',
        'generate_pos_voucher_id',
        'brand_id',
        string='Selected Brand'
    )

    def _compute_get_no_of_used(self):
        for data in self:
            data.no_of_used = len(data.use_history_ids.ids)

    def generate_vouchers(self):
        self.ensure_one()
        if self.no_of_usage > 0 and self.no_of_used >= self.no_of_usage:
            raise ValidationError(_( "Generate pos voucher already has exceeded the limit usage"))
        return {
            'name': ("Generate Voucher"),
            'type': 'ir.actions.act_window',
            'res_model': 'generate.pos.voucher.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {}
        }

    def generate_from_ui_pos(self,receipt_template_id,total):
        self.ensure_one()
        wizard_obj = self.env['generate.pos.voucher.wizard']
        total = float(total)
        result = False
        if (self.no_of_usage == 0 or self.no_of_used < self.no_of_usage) and self.minimum_spend <= total:
            vouchers = wizard_obj.with_context(active_id=self.id,receipt_template_id=receipt_template_id).create({'no_of_voucher':1,'amount_of_usage':1,}).action_confirm()
            if vouchers:
                result = vouchers[0]
                result = {'number':result.number,'apply_type':result.apply_type,'end_date':result.end_date,'value':result.value,'minimum_purchase_amount':result.minimum_purchase_amount}
        return result

    @api.model
    def create(self, vals):
        vals = self.remove_whitespace(vals)
        vals['name'] = self.env['ir.sequence'].next_by_code('generate.pos.voucher') or _('New')
        voucher = super(GeneratePosVoucher, self).create(vals)
        for rec in voucher:
            rec.validate()
        return voucher

    def write(self, vals):
        vals = self.remove_whitespace(vals)
        res = super(GeneratePosVoucher, self).write(vals)
        for rec in self:
            rec.validate()
        return res

    def validate(self):
        self.ensure_one()
        if self.is_customize_sequence:
            if self.sequence_generate_method == 'Running Number':
                if self.running_number_prefix and self.running_number_prefix not in ['',False]:
                    domain = [('running_number_prefix','=', self.running_number_prefix), ('id','!=', self.id)]
                    count = self.env[self._name].search_count(domain)
                    if count:
                        raise UserError(_("You can't create 2 Generate Voucher with the same Prefix (%s)" % str(self.running_number_prefix)))

            if self.sequence_generate_method == 'Manual Input':
                if self.manual_input_sequence and self.manual_input_sequence not in ['',False]:
                    domain = [('manual_input_sequence','=', self.manual_input_sequence), ('id','!=', self.id)]
                    count = self.env[self._name].search_count(domain)
                    if count:
                        raise UserError(_("You can't create 2 Generate Voucher with the same Manual Input Sequence (%s)" % str(self.manual_input_sequence)))

    def remove_whitespace(self, vals):
        _fields = ['manual_input_sequence','running_number_prefix']
        for _field in _fields:
            if _field in vals and vals[_field] not in ['', False]:
                vals[_field] = str(vals[_field]).strip().replace(' ','')
        return vals

    @api.constrains('running_number_digit')
    def _check_running_number_digit(self):
        for record in self.filtered(lambda o: o.is_customize_sequence):
            if record.running_number_digit < 1:
                raise ValidationError(_('Digit must be positive!'))

    @api.constrains('running_number_digit', 'running_number_current_sequence')
    def _check_running_number_digit_consistency(self):
        for record in self.filtered(lambda o: o.is_customize_sequence):
            current_sequence = record.running_number_current_sequence
            if record.running_number_digit != len(current_sequence) and len(str(int(current_sequence))) <= record.running_number_digit:
                raise ValidationError(_('The length of sequence (%s) is %s while running_number_digit is %s!' % (current_sequence, len(current_sequence), record.running_number_digit)))

    @api.onchange('running_number_digit')
    def _onchange_running_number_digit(self):
        if self.is_customize_sequence and self.running_number_digit > 1:
            self.running_number_current_sequence = str(int(self.running_number_current_sequence)).zfill(self.running_number_digit)


class GeneratePosVoucherUseHistory(models.Model):
    _name = "generate.pos.voucher.use.history"
    _description = "Histories Generate use voucher of customer"

    pos_order_id = fields.Many2one('pos.order', string='Order')
    payment_id = fields.Many2one('pos.payment', string='Payment')
    voucher_id = fields.Many2one('generate.pos.voucher', required=1, string='Voucher', ondelete='cascade')
    value = fields.Float('Value Redeem', required=0)
    used_date = fields.Datetime('Used Date', required=1)
    cashier_id = fields.Many2one('res.users', 'Cashier Added')