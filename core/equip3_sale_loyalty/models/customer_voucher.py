from odoo import models,fields,api,_
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta

class CustomerVoucher(models.Model):
    _name = 'customer.voucher'
    _description = 'Customer Voucher'

    name = fields.Char(string='Number', default='/', copy=False, readonly=True)
    customer_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    customer_target_id = fields.Many2one(comodel_name='customer.target', string='Customer Target')
    state = fields.Selection(string='State', selection=[('available', 'Available'),('used', 'Used'),('expired','Expired')], default="available", compute="_compute_state", store=True)
    start_date = fields.Date(string='Start Date', related="customer_target_id.start_date", store=True)
    end_date = fields.Date(string='End Date', related="customer_target_id.end_date", store=True)
    reward_type = fields.Selection(string="Reward Type", related='customer_target_id.reward_type',)
    discount_line_product_id = fields.Many2one('product.product', string='Reward Line Product',related="customer_target_id.discount_line_product_id")
    sale_order_line_ids = fields.One2many(comodel_name='sale.order.line', inverse_name='customer_voucher_id', string='Sale Order Line')
    cashback_line_ids = fields.One2many(comodel_name='cashback.line', inverse_name='customer_voucher_id', string='Cashback Line')
    creation_date = fields.Date(string='Creation Date')
    expired_date = fields.Date(string='Expired Date',compute='_compute_expired_date', store=True)
    expiration_period = fields.Integer(string='Voucher Expiration (days)', related='customer_target_id.voucher_expiration', readonly=True)
    customer_voucher_type = fields.Selection(string='Customer Voucher Type', related='customer_target_id.voucher_type', readonly=True)
    is_apply_voucher = fields.Boolean(string='Applied Vouchers', default=False, store=True)   
    
    
    @api.depends('creation_date', 'expiration_period')
    def _compute_expired_date(self):
        for voucher in self:
            if voucher.creation_date:
                voucher.expired_date = voucher.creation_date + relativedelta(days=voucher.expiration_period)

    @api.depends('sale_order_line_ids','cashback_line_ids')
    def _compute_state(self):
        for i in self:
            today = fields.Date.today()
            if not i.end_date:
                i.state = 'expired'
            else:
                if i.expired_date and i.expired_date < today:
                    i.state = 'expired'
                elif i.sale_order_line_ids or i.cashback_line_ids:
                    i.state = 'used'
                else:
                    i.state = 'available'

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('customer.voucher') or _('/')
        program = super(CustomerVoucher,self).create(vals)
        program.name = program.name.replace('NOCUSTOMERTARGET',program.customer_target_id and program.customer_target_id.name or '')
        return program

    def get_expiry_voucher(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        template_id = self.env.ref('equip3_sale_loyalty.email_template_expiry_voucher')
        notifications_expiry_voucher = bool(IrConfigParam.get_param("notifications_expiry_voucher"))
        notifications_time = int(IrConfigParam.get_param('notifications_time'))
        date = False
        if notifications_time:
            date = datetime.today().date() + relativedelta(days=notifications_time)
        if notifications_expiry_voucher:
            customer_ids = self.env['customer.voucher'].search([]).mapped('customer_id')
            if customer_ids:
                for customer_id in customer_ids:
                    expiry_vouchers = self.env['customer.voucher'].search([('customer_id','=',customer_id.id),('expired_date','=',date)])
                    if expiry_vouchers:
                        ctx = {
                            'email_from' : self.env.user.company_id.email,
                            'email_to' : customer_id.email,
                            'expiry_date': date,
                            'list_voucher': expiry_vouchers
                        }
                        template_id.with_context(ctx).send_mail(expiry_vouchers[0].id)




    