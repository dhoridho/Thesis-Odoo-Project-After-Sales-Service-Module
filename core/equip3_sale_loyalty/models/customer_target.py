from odoo import models,fields,api,_
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from operator import itemgetter

class CustomerTarget(models.Model):
    _name = 'customer.target'
    _description = 'Customer Target'

    name = fields.Char(string='Number', default='New', copy=False, readonly=True)
    res_name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self:self.env.company, readonly=True)
    applied_to = fields.Selection(string='Applied To', selection=[('all', 'All Customers'), ('category', 'Customer Category'), ('selected', 'Selected Customers')], default='all', required=True)
    customer_categ_id = fields.Many2one(comodel_name='customer.category', string='Customer Category')
    partner_ids = fields.Many2many(comodel_name='res.partner', string='Selected Customers', domain="[('is_customer','=',True)]")
    target_amount = fields.Monetary('Target Amount', required=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', related='company_id.currency_id')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    reward_type = fields.Selection(string='Reward', selection=[('discount', 'Discount'), ('product', 'Free Product'),('cashback', 'Cashback'),], default="discount",required=True)
    disc_type = fields.Selection(string='Apply Discount', selection=[('fix', 'Fixed Amount'), ('percentage', 'Percentage'),], default="fix")
    disc_amount = fields.Monetary('Fixed Amount')
    disc_percentage = fields.Float(string='Percentage')
    product_id = fields.Many2one(comodel_name='product.product', string='Free Product')
    quantity = fields.Float(string='Quantity', default=1)
    discount_line_product_id = fields.Many2one('product.product', string='Reward Line Product', copy=False,
        help="Product used in the sales order to apply the discount. Each coupon program has its own reward product for reporting purpose")
    customer_voucher_ids = fields.One2many(comodel_name='customer.voucher', inverse_name='customer_target_id', string='Vouchers')
    customer_voucher_count = fields.Integer(string='Customer Voucher Count', compute="_compute_customer_voucher_count")
    apply_cashback = fields.Selection(string='Apply Cashback', selection=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')], default="percentage")
    percentage = fields.Float("Percentage")
    fixed_amount = fields.Float("Fixed Amount")
    voucher_type = fields.Selection( selection=[('single', 'Single Voucher'),('multi','Multi Voucher')], string='Voucher Type', default="single")
    voucher_expiration = fields.Integer(string='Voucher Expiration', required=True)
    expired = fields.Boolean("Expired")
    level_applied = fields.Integer("Level", compute='_compute_level_applied_to', store=True)

    @api.depends('applied_to')
    def _compute_level_applied_to(self):
        for rec in self:
            if rec.applied_to == 'all':
                rec.level_applied = 3
            elif rec.applied_to == 'category':
                rec.level_applied = 2
            elif rec.level_applied == 'selected':
                rec.level_applied = 1

    def get_expiry_cust_target(self):
        self.env.cr.execute("""
            SELECT id
            FROM customer_target
            WHERE expired = False AND end_date < %s""", (fields.Date.today().strftime("%Y%m%d")))
        target_ids = self.env.cr.dictfetchall()
        target_ids = list(map(itemgetter('id'), target_ids))
        self._cr.execute("""UPDATE customer_target SET expired = True WHERE id in %s""", [tuple(target_ids)])
        self._cr.commit()
    
    @api.constrains('voucher_expiration')
    def _check_voucher_expiration(self):
        for record in self:
            if record.voucher_expiration <= 0:
                raise ValidationError("The value of Voucher Expiration must be greater than 0.")

    @api.constrains('target_amount')
    def _check_target_amount(self):
        for record in self:
            if record.target_amount <= 0:
                raise ValidationError("Target Amount must be greater than 0.")


    @api.depends('customer_voucher_ids')
    def _compute_customer_voucher_count(self):
        for i in self:
            i.customer_voucher_count = len(i.customer_voucher_ids)

    @api.onchange('applied_to','customer_categ_id')
    def _onchange_applied_to(self):
        selected_customers = [(6,0,[])]
        company_id = self.env.company.id
        if self.applied_to == 'category':
            if self.customer_categ_id:
                customers = self.env['res.partner'].sudo().search([
                    ('is_customer','=',True),
                    ('customer_category','=',self.customer_categ_id.id),
                    ('company_id','=',company_id),
                ])
                selected_customers = [(6,0,customers.ids)]
        elif self.applied_to == 'all':
            customers = self.env['res.partner'].sudo().search([
                ('company_id','=',company_id),
                ('is_customer','=',True),
            ])
            selected_customers = [(6,0,customers.ids)]
        self.partner_ids = selected_customers

    @api.constrains('start_date', 'end_date', 'partner_ids')
    def check_date_partner_overlap(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise ValidationError('End date should be greater than start date.')
            domain = [
                ('id', '!=', rec.id),
                ('start_date', '<', rec.end_date),
                ('end_date', '>', rec.start_date - relativedelta(days=1)),
            ]
            if rec.partner_ids:
                domain += [('partner_ids', 'in', rec.partner_ids.ids)]
            overlapping_rec = self.search(domain, limit=1)
            if overlapping_rec:
                raise ValidationError('The dates and partners overlap with another record.')

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('customer.target') or _('New')
        program = super(CustomerTarget,self).create(vals)
        if not vals.get('discount_line_product_id', False):
            values = program._get_discount_product_values()
            discount_line_product_id = self.env['product.product'].create(values)
            program.discount_line_product_id = discount_line_product_id.id
        program.create_voucher()
        return program

    def write(self, vals):
        # if 'partner_ids' in vals:
        #     raise ValidationError(_("You cannot edit 'Applied to' which data is saved!"))
        res = super(CustomerTarget, self).write(vals)
        reward_fields = [
            'reward_type', 'disc_type', 'disc_amount', 'disc_percentage', 'product_id', 'free_product_line_ids'
        ]
        if any(field in reward_fields for field in vals):
            name = self._get_name_product_reward()
            self.discount_line_product_id.name = name
        return res
    
    def _get_discount_product_values(self):
        name = self._get_name_product_reward()
        categ_id = self.env.ref('equip3_sale_promo_coupon.product_category_product_rewards').id
        lst_price = 0
        if self.reward_type == 'cashback':
            if self.apply_cashback == 'percentage':
                lst_price = self.percentage
            else:
                lst_price = self.fixed_amount
        return {
            'name': name,
            'type': 'service',
            'categ_id': categ_id,
            'taxes_id': False,
            'supplier_taxes_id': False,
            'sale_ok': False,
            'purchase_ok': False,
            'lst_price': lst_price, #Do not set a high value to avoid issue with coupon code
        }

    def _get_name_product_reward(self):
        name = ''
        if self.reward_type == 'discount':
            if self.disc_type == 'fix':
                name = 'Discount {} {} on total amount'.format(self.disc_amount,self.currency_id.name)
            elif self.disc_type == 'percentage':
                name = 'Discount {}% on total amount'.format(self.disc_percentage,self.currency_id.name)
        elif self.reward_type == 'product':
            name = 'Free product - {}'.format(','.join(self.free_product_line_ids.mapped('product_id.name')))
        elif self.reward_type == 'cashback':
            name = 'Cashback - {}'.format(self.fixed_amount if self.apply_cashback == 'fixed' else (str(self.percentage)+"%"))
        return name

    
    def create_voucher(self):
        for partner in self.partner_ids:
            customer_target_id = self
            if partner.customer_target_id:
                if partner.level_applied < customer_target_id.level_applied:
                    continue
            partner.customer_target_id = customer_target_id.id
            partner.done = False
            partner.remaining_amount_cust_target = 0
            partner.update_customer_target()
    
    
    def action_open_customer_voucher(self):
        action = {
                'name': _('Customer Voucher'),
                'view_mode': 'tree,form',
                'res_model': 'customer.voucher',
                'type': 'ir.actions.act_window',
                'target': 'self',
                'domain':[('customer_target_id','=',self.id)]
            }
        return action