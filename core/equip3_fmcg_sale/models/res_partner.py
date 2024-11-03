from odoo import models,fields,api,_
from datetime import date, datetime,timedelta


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_get(self, fields_list):
        res = super(ResPartnerInherit, self).default_get(fields_list)
        res.update({
                'set_customer_credit_limit_per_brand': True
        })
        return res

    bank_guarantee_amount = fields.Float(string='Bank Guarantee Amount')
    bank_guarantee_amount_per_brand = fields.Float(string='Bank Guarantee Amount per Brand', compute="_compute_bank_guarantee_amount_per_brand")
    bank_guarantee_exp_date = fields.Date(string='Expiration Date')
    is_increase_credit_limit = fields.Boolean(string='Increase Credit Limit', default=True)
    stock_life_ids = fields.One2many('stock.life','is_customer', string="Stock Life")   

    @api.depends('bank_guarantee_amount','product_brand_ids')
    def _compute_bank_guarantee_amount_per_brand(self):
        for i in self:
            i.bank_guarantee_amount_per_brand = i.product_brand_ids and i.bank_guarantee_amount/len(i.product_brand_ids) or 0

    # OVERRIDE
    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.state', 'sale_order_ids', 'sale_order_ids.amount_total', 'sale_order_ids.state', 'cust_credit_limit','bank_guarantee_amount','is_increase_credit_limit','bank_guarantee_exp_date')
    def _compute_customer_credit_limit(self):
        for record in self:
            sale_ids = record.sale_order_ids.filtered(lambda l: l.state in ('sale','done'))
            sale_amount = sum(sale_ids.mapped('amount_total'))
            today = date.today()
            allocation_bank_guarantee_amount = 0
            if record.bank_guarantee_exp_date and record.bank_guarantee_exp_date >= today and record.is_increase_credit_limit:
                allocation_bank_guarantee_amount = record.bank_guarantee_amount
            record.customer_credit_limit = record.cust_credit_limit + allocation_bank_guarantee_amount - sale_amount
    
    
    # Cron Method
    def cron_send_email_expiry_bank_guarantee(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        template_id = self.env.ref('equip3_fmcg_sale.email_template_expiry_customer_bank_guarantee')
        notifications_expiry_customer_bank_guarantee = bool(IrConfigParam.get_param("notifications_expiry_customer_bank_guarantee"))
        notifications_expiry_customer_bank_guarantee_time = int(IrConfigParam.get_param('notifications_expiry_customer_bank_guarantee_time'))
        date = False
        if notifications_expiry_customer_bank_guarantee_time:
            date = datetime.today().date() + timedelta(days=notifications_expiry_customer_bank_guarantee_time)
        if notifications_expiry_customer_bank_guarantee and date:
            customer_ids = self.search([
                ('bank_guarantee_exp_date','=',date)
            ])
            for customer_id in customer_ids:
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : customer_id.email,
                    'expiry_date': date,
                    'customer_name': customer_id.name or '',
                }
                template_id.with_context(ctx).send_mail(customer_id.id)
            customer_ids = self.search([
                ('bank_guarantee_exp_date','=',date.today())
            ])
            for customer_id in customer_ids:
                for line in customer_id.product_brand_ids:
                    line.request_allocation_bank_guarantee_amount = 0


class CreditLimitProductBrandInherit(models.Model):
    _inherit = 'credit.limit.product.brand'

    allocation_bank_guarantee_amount = fields.Float(string='Allocation Bank Guarantee', compute="_compute_customer_avail_credit_limit")
    request_allocation_bank_guarantee_amount = fields.Float(string='Allocation Bank Guarantee (Request)',)
    res_request_allocation_bank_guarantee_amount = fields.Float(string='Res Allocation Bank Guarantee (Request)',)
    last_request_allocation_bank_guarantee_amount = fields.Float(string='Last Allocation Bank Guarantee',)
    state = fields.Selection(related="limit_request_id.state")

    def _compute_customer_avail_credit_limit(self):
        for record in self:
            sale_ids = self.env['sale.order'].search([
                ('partner_id', '=', record.partner_id.id),
                ('brand', '=', record.brand_id.id),
                ('state', '=', 'sale'),
            ])
            invoice_ids = sale_ids.invoice_ids
            invoice_amount =  sum(invoice_ids.mapped('amount_total')) - sum(invoice_ids.mapped('amount_residual'))
            today = date.today()
            is_increase_credit_limit = False
            if record.partner_id.is_increase_credit_limit and (not record.partner_id.bank_guarantee_exp_date or (record.partner_id.bank_guarantee_exp_date and record.partner_id.bank_guarantee_exp_date >= today)):
                is_increase_credit_limit = True
            allocation_bank_guarantee_amount = is_increase_credit_limit and 0
            if not record.partner_id.is_increase_credit_limit:
                if record.request_allocation_bank_guarantee_amount:
                    record.res_request_allocation_bank_guarantee_amount = record.request_allocation_bank_guarantee_amount
                record.request_allocation_bank_guarantee_amount = 0
            if record.request_allocation_bank_guarantee_amount and is_increase_credit_limit:
                allocation_bank_guarantee_amount = record.request_allocation_bank_guarantee_amount
            if record.partner_id.is_increase_credit_limit and not record.request_allocation_bank_guarantee_amount:
                allocation_bank_guarantee_amount = record.res_request_allocation_bank_guarantee_amount
            record.update({
                'customer_avail_credit_limit' : record.customer_credit_limit + allocation_bank_guarantee_amount - sum(sale_ids.mapped('amount_total')) + invoice_amount,
                'allocation_bank_guarantee_amount':allocation_bank_guarantee_amount
            })