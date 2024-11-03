# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosCouponProgram(models.Model):
    _name = 'pos.coupon.program'
    _description = 'POS Coupon Program'

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    coupon_name = fields.Char('Coupon Name', required=True)
    type_apply = fields.Selection([('Specific Product','Specific Product')], string='Type Apply', required=True, default='Specific Product')
    base_on_product_id = fields.Many2one('product.product', string='Product Based On')
    minimum_purchase_quantity = fields.Integer('Minimum Purchase Quantity', default=1)
    sequence_generate_method = fields.Selection([
        ('Manual Input','Manual Input'),
        ('EAN13','EAN13'),
    ], string='Sequence Generate Method', required=True, help='If coupon sequence generate method = EAN13, then automatically generate')
    manual_input_sequence = fields.Char('Manual Input sequence')

    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('Expired Date')
    no_of_usage = fields.Integer('No of Usage', help='The number of each coupon usage, if 0 = unlimited')
    no_of_used = fields.Integer('No Of Used', compute='_compute_no_of_used')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    state = fields.Selection([
        ('draft','Draft'), 
        ('active','Active'), 
        ('used','Used'),
    ], string='Status', default='draft')

    reward_type = fields.Selection([
        ('Discount','Discount'),
        ('Free Item','Free Item'),
    ], string='Reward Type', required=True, default='Discount',
    help='Discount = Reward will be provided as discount\nFree item = Reward will be provided as free product')
    reward_product_id = fields.Many2one('product.product', string='Reward Product gift')
    reward_quantity = fields.Integer('Reward Quantity')
    reward_discount_type = fields.Selection([('Fixed','Fixed'),('Percentage','Percentage')], string='Discount Type', default='Fixed')
    reward_discount_amount = fields.Integer('Reward Discount Amount')
    reward_max_discount_amount = fields.Float('Reward Max. Discount Amount')

    pos_coupon_count = fields.Integer('Coupon Count', compute='_compute_pos_coupon_count')

    @api.model
    def create(self, vals):
        vals = self.remove_whitespace(vals)
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pos.coupon.program') or _('New')
        res = super(PosCouponProgram, self).create(vals)
        for rec in res:
            rec.validate()
        return res

    def write(self, vals):
        vals = self.remove_whitespace(vals)
        res = super(PosCouponProgram, self).write(vals)
        for rec in self:
            rec.validate()
        return res

    def validate(self):
        self.ensure_one()
        if self.start_date and self.end_date and (self.end_date <= self.start_date):
            raise UserError(_("Expired Date should after Start Date"))

        if self.sequence_generate_method == 'Manual Input':
            if self.manual_input_sequence and self.manual_input_sequence not in ['',False]:
                domain = [('manual_input_sequence','=', self.manual_input_sequence), ('id','!=', self.id)]
                program_count = self.env[self._name].search_count(domain)
                if program_count:
                    raise UserError(_("You can't create 2 Coupon Program with the same Manual Input Sequence (%s)" % str(self.manual_input_sequence)))

    def remove_whitespace(self, vals):
        _fields = ['manual_input_sequence']
        for _field in _fields:
            if _field in vals and vals[_field] not in ['', False]:
                vals[_field] = str(vals[_field]).strip().replace(' ','')
        return vals

    def _compute_no_of_used(self):
        result = {}
        if self:
            query = '''
                SELECT c.coupon_program_id, COUNT(h.id)
                FROM pos_coupon_use_history AS h
                INNER JOIN pos_coupon AS c ON c.id = h.coupon_id
                WHERE c.coupon_program_id IN (%s)
                GROUP BY c.coupon_program_id
            ''' % (str(self.ids)[1:-1])
            self._cr.execute(query)
            result = dict(self._cr.fetchall())
        for rec in self:
            rec.no_of_used = result.get(rec.id, 0)

    def _compute_pos_coupon_count(self):
        result = {}
        if self:
            query = '''
                SELECT coupon_program_id, COUNT(id)
                FROM pos_coupon
                WHERE coupon_program_id IN (%s)
                GROUP BY coupon_program_id
            ''' % (str(self.ids)[1:-1])
            self._cr.execute(query)
            result = dict(self._cr.fetchall())
        for rec in self:
            rec.pos_coupon_count = result.get(rec.id, 0)

    def action_view_coupons(self):
        self.ensure_one()
        context = dict(self._context, create=False)
        return {
            'name': _('Coupons'),
            'view_mode': 'tree,form',
            'res_model': 'pos.coupon',
            'type': 'ir.actions.act_window',
            'domain': [('coupon_program_id', '=', self.id)],
            'context': context
        }

    def action_generate(self):
        self.ensure_one()
        context = {
            'default_coupon_program_id': self.id,
        }
        return {
            'name': _('Generate Coupon'),
            'view_mode': 'form',
            'res_model': 'pos.coupon.generate.wizard',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }