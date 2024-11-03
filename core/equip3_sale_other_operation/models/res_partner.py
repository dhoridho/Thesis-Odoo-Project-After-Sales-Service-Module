
from odoo import api , fields , models
from datetime import datetime, date
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import json

class CreditLimitProductBrand(models.Model):
    _name = 'credit.limit.product.brand'
    _description = "Credit Limit Product Brand"

    @api.model
    def default_get(self, fields):
        res = super(CreditLimitProductBrand, self).default_get(fields)
        # customer_credit_limit = self.env['ir.config_parameter'].sudo().get_param('customer_credit_limit', 1000000)
        # res['customer_credit_limit'] = customer_credit_limit
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'product_brand_ids' in context_keys:
                if len(self._context.get('product_brand_ids')) > 0:
                    next_sequence = len(self._context.get('product_brand_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    partner_id = fields.Many2one('res.partner', string="Partner")
    brand_id = fields.Many2one('product.brand', string='Brand')
    customer_credit_limit = fields.Float("Customer Credit Limit", default=0)
    customer_avail_credit_limit = fields.Float("Customer Available Credit Limit", default=0, compute="_compute_customer_avail_credit_limit", store=False)
    new_credit_limit_amount = fields.Integer("New Credit Limit Amount")
    last_credit_limit_amount = fields.Integer("Last Credit Limit Amount")
    sequence = fields.Integer(string="Sequence")
    sequence2 = fields.Integer(string="No.", related="sequence", readonly=True, store=True)
    limit_request_id = fields.Many2one('limit.request', string="Limit Request")
    brand_ids = fields.Many2many(related='limit_request_id.brand_ids')

    customer_esignature = fields.Boolean(string="Customer Signature")
    identity_number = fields.Char(string="Identity Number")
    signature_name = fields.Char(string="Full Name")
    date_of_birth = fields.Date(string="Date Of Birth")
    signature_mobile = fields.Char(string="Phone")
    signature_status = fields.Char(string="Status")
    signature_email = fields.Char(string="Email")
    selfie_img = fields.Binary(string="Selfie Image", attachment=True)
    selfie_img_name = fields.Char(string='Selfie Image Name', default='selfie.png')
    identity_image = fields.Binary(string="Identity Id", attachment=True)
    identity_image_name = fields.Char(string="Identity Image Name", default="identity.png")
    signature_country_id = fields.Many2one('res.country', string="Country")
    signature_reason = fields.Char(string="Reason")
    signature_token = fields.Char(string='Token')
    signature_privy_id = fields.Char(string="Privy Id")

    @api.onchange('new_credit_limit_amount')
    def set_amount(self):
        for rec in self:
            if rec.limit_request_id:
                rec.limit_request_id._get_limit_matrix()

    def _compute_customer_avail_credit_limit(self):
        for record in self:
            sale_ids = self.env['sale.order'].search([
                ('partner_id', '=', record.partner_id.id),
                ('brand', '=', record.brand_id.id),
                ('state', '=', 'sale'),
            ])
            invoice_ids = sale_ids.invoice_ids
            invoice_amount =  sum(invoice_ids.mapped('amount_total')) - sum(invoice_ids.mapped('amount_residual'))
            record.customer_avail_credit_limit = record.customer_credit_limit - sum(sale_ids.mapped('amount_total')) + invoice_amount

    def unlink(self):
        partner_id = self.partner_id
        res = super(CreditLimitProductBrand, self).unlink()
        partner_id._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(CreditLimitProductBrand, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.partner_id._reset_sequence()
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer_invoice_overdue = fields.Boolean(string="Set Customer Invoice Overdue Days ?", tracking=True)
    customer_max_invoice_overdue = fields.Float(string="Customer Max Invoice Overdue Days", tracking=True)
    is_set_customer_on_hold = fields.Boolean(string="Set Customer On Hold (Invoice Overdue)", tracking=True)
    customer_credit = fields.Boolean('Set Customer Credit Limit ?', tracking=True)

    customer_credit_limit = fields.Float('Customer Available Credit Limit', compute="_compute_customer_credit_limit", store=True, tracking=True)

    set_customer_onhold = fields.Boolean(
        'Customer on Hold if Credit Limit Exceed', tracking=True)
    cust_credit_limit = fields.Float('Customer Credit Limit')

    is_over_credit_limit = fields.Boolean(string="Over Credit Limit", compute='_compute_over_limit_matrix')
    is_invoice_overdue = fields.Boolean(string="Invoice Overdue", compute='_compute_over_limit_matrix')
    open_invoice_limit = fields.Boolean(string="Open Invoice Limit", compute='_compute_over_limit_matrix')
    
    is_open_invoice_limit = fields.Boolean(string="Set Customer Number Open Invoice Limit ?", tracking=True)
    no_open_inv_limit = fields.Float(string="Number of Open Invoices Limit", tracking=True)
    avl_open_inv_limt = fields.Float(string="Available Open Invoices Quota", tracking=True, compute='_compute_open_limit', store=True)
    customer_on_hold_open_invoice = fields.Boolean(string="Customer On Hold If Number Open Invoice Exceed")
    set_customer_credit_limit_per_brand = fields.Boolean(
        'Customer Credit Limit per Brand', tracking=True)
    product_brand_ids = fields.One2many('credit.limit.product.brand', 'partner_id', string="Products")
    filter_brand_ids = fields.Char(string='Brand',compute='_compute_brand_id', store=False)
    customer_over_limit = fields.Boolean("Allow Over Limit?")
    customer_product_label_ids = fields.One2many('customer.product.template.line','customer_id', string="Product Label Line")
    customer_product_template_ids = fields.One2many('customer.product.template','customer_id', string="Product Label")
    show_customer_product_label = fields.Boolean('Show Customer Product Label Configuration', compute="_compute_show_customer_product_label")
    def _compute_show_customer_product_label(self):
        self.show_customer_product_label = self.env['ir.config_parameter'].sudo().get_param('show_customer_product_label', False)

    @api.depends('product_brand_ids', 'product_brand_ids.brand_id')
    def _compute_brand_id(self):
        for record in self:
            record.filter_brand_ids = json.dumps([('id', 'in', record.product_brand_ids.mapped('brand_id').ids)])

    def get_date(self):
        return datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    # @api.onchange('name')
    # def _onchange_name(self):
    #     self._compute_over_limit_matrix()
    #     self._compute_open_limit()

    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.amount_residual', 'invoice_ids.state', 'sale_order_ids', 'sale_order_ids.amount_total', 'sale_order_ids.state', 'cust_credit_limit')
    def _compute_customer_credit_limit(self):
        for record in self:
            sale_ids = record.sale_order_ids.filtered(lambda l: l.state in ('sale','done'))
            sale_amount = sum(sale_ids.mapped('amount_total'))
            record.customer_credit_limit = record.cust_credit_limit - sale_amount

    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.state', 'no_open_inv_limit','name')
    def _compute_open_limit(self):
        for record in self:
            invoice_id = len(record.invoice_ids.filtered(lambda l: l.payment_state in ('not_paid', 'in_payment', 'partial')))
            avl_limit = record.no_open_inv_limit - invoice_id
            record.avl_open_inv_limt = avl_limit

    @api.model
    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        credit_limit =  IrConfigParam.get_param('customer_credit_limit', 1000000)
        res['cust_credit_limit'] = credit_limit
        res['customer_credit_limit'] = credit_limit
        max_invoice_overdue_days = IrConfigParam.get_param('customer_max_invoice_overdue_days', 30)
        res['customer_max_invoice_overdue'] = max_invoice_overdue_days
        customer_open_invoice_limit = IrConfigParam.get_param('customer_open_invoice_limit', 0)
        res['no_open_inv_limit'] = customer_open_invoice_limit
        return res

    @api.depends('name')
    def _compute_over_limit_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_over_credit_limit = IrConfigParam.get_param('is_over_credit_limit', False)
        is_invoice_overdue = IrConfigParam.get_param('is_invoice_overdue', False)
        open_invoice_limit = IrConfigParam.get_param('open_invoice_limit', False)
        for record in self:
            record.is_over_credit_limit = is_over_credit_limit
            record.is_invoice_overdue = is_invoice_overdue
            record.open_invoice_limit = open_invoice_limit

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.product_brand_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange('is_customer_invoice_overdue')
    def onchange_is_customer_invoice_overdue(self):
        if self.is_customer_invoice_overdue == True:
            self.is_set_customer_on_hold = True

    @api.onchange('customer_credit')
    def onchange_customer_credit(self):
        if self.customer_credit == True:
            self.set_customer_onhold = True
        else:
            self.customer_over_limit = False

    @api.onchange('is_open_invoice_limit')
    def onchange_is_open_invoice_limit(self):
        if self.is_open_invoice_limit == True:
            self.customer_on_hold_open_invoice = True

    
    
