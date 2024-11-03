
from odoo import api, fields, models, _
from odoo.exceptions import UserError , ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    state = fields.Selection(selection_add=[
        ('retreat', 'Retreated'),
        ('cancel',)
    ])
    tender_scope = fields.Selection(string='Tender Scope', related="agreement_id.tender_scope", store=True)
    is_submit_quotation = fields.Boolean(string='Submit Quotation')
    hide_cancel = fields.Boolean("Hide Cancel", compute='_compute_hide_cancel', store=False)

    def _compute_hide_cancel(self):
        for rec in self:
            if rec.sh_partially_ship or rec.sh_partially_paid or rec.sh_fully_ship or rec.sh_fully_paid or rec.state in ('waiting_for_approve', 'cancel', 'request_for_amendment', 'retreat'):
                rec.hide_cancel = True
            else:
                rec.hide_cancel = False

    # OVERRIDE sh_po_tender_management
    @api.depends('partner_id')
    def _compute_sh_msg(self):
        if self:
            for rec in self:
                rec.sh_msg = ''
                if rec.agreement_id and not rec.agreement_id.tender_scope == 'open_tender' and rec.partner_id.id not in rec.agreement_id.partner_ids.ids:
                    rec.sh_msg = 'Vendor you have selected not exist in selected tender. You can still create quotation for that.'

    # amount_untaxed2 = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all2')
    # amount_tax2 = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all2')
    # amount_total2 = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all2')
    #
    # @api.depends('order_line.price_total', 'order_line.price_total2')
    # def _amount_all2(self):
    #     for order in self:
    #         update = False
    #         amount_untaxed = amount_tax = 0.0
    #         for line in order.order_line:
    #             if line.res_bid:
    #                 update = True
    #                 line._compute_amount2()
    #                 amount_untaxed += line.price_subtotal2
    #                 amount_tax += line.price_tax2
    #         order.update({
    #             'amount_untaxed2': order.currency_id.round(amount_untaxed),
    #             'amount_tax2': order.currency_id.round(amount_tax),
    #             'amount_total2': amount_untaxed + amount_tax,
    #         })
    #         if update:
    #             order.update({
    #                 'amount_untaxed': order.amount_untaxed2,
    #                 'amount_tax': order.amount_tax2,
    #                 'amount_total': order.amount_total2,
    #             })

    # price_rating = fields.Char(string='Price Rating', compute="_compute_price_rating")
    price_rating = fields.Selection(string='Price Rating', selection=[
        ('beaten', 'Your Price Has been beaten by another vendor'), 
        ('competitive', 'You have the most competitive price'),
        ('highest', 'You have the highest price'),
        ('empty', '-')
        ], compute="_compute_price_rating", store=True)
    

    @api.depends('amount_total')
    def _compute_price_rating(self):
        for i in self:
            price_rating = ''
            if i.agreement_id:
                purchase_orders = self.env['purchase.order'].sudo().search([
                    ('agreement_id','=',i.agreement_id.id), ('state', 'in', ['draft']), ('selected_order', '=', False)
                ], order="amount_total desc")
                if purchase_orders:
                    amount_total_list = purchase_orders.mapped('amount_total')
                    if len(amount_total_list) > 1 and purchase_orders[0].amount_total*len(amount_total_list) == sum(amount_total_list):
                        price_rating = 'beaten'
                    elif i.id == purchase_orders[-1].id:
                        price_rating = 'competitive'
                    elif i.id == purchase_orders[0].id:
                        price_rating = 'highest'
                    else:
                        price_rating = 'beaten'
                else:
                    price_rating = 'empty'
            i.price_rating = price_rating

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bid = fields.Float('Vendor Bid', digits='Product Price')
    # price_subtotal2 = fields.Monetary(compute='_compute_amount2', string='Cost Saving Subtotal', store=True)
    # res_bid = fields.Float('Bid Price', digits='Product Price')
    cost_saving = fields.Float('Cost Saving', digits='Product Price', compute='_compute_cost_saving', store=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', related='order_id.payment_term_id')
    # price_total2 = fields.Monetary(compute='_compute_amount2', string='Total', store=True)
    # price_tax2 = fields.Float(compute='_compute_amount2', string='Tax', store=True)
    base_price = fields.Float('Base Price', digits='Product Price', compute='_compute_base_price', store=True)
    update_base = fields.Boolean("Update Base Price")
    lead_time = fields.Char(string='Lead Time', compute="_compute_lead_time", compute_sudo=True)
    feedback = fields.Char(string='Feedback', readonly=True)
    company_size = fields.Char("Company Size", compute="_compute_lead_time", store=True)
    capital_revenue = fields.Float("Capital Revenue", related="partner_id.capital_revenue", store=True)
    base_quantity = fields.Float(string='Base Quantity')

    # @api.constrains('product_qty')
    # def _check_min_qty(self):
    #     for record in self:
    #         if record.product_qty < 1:
    #             record.product_qty = 1

    @api.depends('product_id','partner_id')
    def _compute_lead_time(self):
        for rec in self:
            lead_time = ''
            if rec.product_id and rec.partner_id:
                # vendor_pricelist = self.env['product.supplierinfo'].sudo().search([
                #     ('name','=',rec.partner_id.id),
                #     ('product_tmpl_id','=',rec.product_id.product_tmpl_id.id),
                #     ('state1', '=', 'approved')
                # ],limit=1)
                self.env.cr.execute("""
                    SELECT delay
                    FROM product_supplierinfo
                    WHERE name = %s AND product_tmpl_id = %s and state = 'approved' LIMIT 1
                """ % (rec.partner_id.id,rec.product_id.product_tmpl_id.id))
                vendor_pricelist = self.env.cr.fetchall()
                if vendor_pricelist:
                    delay = vendor_pricelist[0]
                    lead_time = '{} days'.format(delay)
            rec.lead_time = lead_time
            if rec.partner_id.company_size or rec.partner_id.company_size:
                rec.company_size = str(rec.partner_id.company_size) + " - " + str(rec.partner_id.company_size2)
            else:
                rec.company_size = "-"

    # @api.depends('product_qty', 'price_unit', 'taxes_id', 'res_bid')
    # def _compute_amount2(self):
    #     for line in self:
    #         vals = line._prepare_compute_all_values2()
    #         taxes = line.taxes_id.compute_all(
    #             vals['res_bid'],
    #             vals['currency_id'],
    #             vals['product_qty'],
    #             vals['product'],
    #             vals['partner'])
    #         line.update({
    #             'price_tax2': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
    #             'price_total2': taxes['total_included'],
    #             'price_subtotal2': taxes['total_excluded'],
    #         })

    # def _prepare_compute_all_values2(self):
    #     # Hook method to returns the different argument values for the
    #     # compute_all method, due to the fact that discounts mechanism
    #     # is not implemented yet on the purchase orders.
    #     # This method should disappear as soon as this feature is
    #     # also introduced like in the sales module.
    #     self.ensure_one()
    #     return {
    #         'res_bid': self.res_bid,
    #         'currency_id': self.order_id.currency_id,
    #         'product_qty': self.product_qty,
    #         'product': self.product_id,
    #         'partner': self.order_id.partner_id,
    #     }

    @api.depends('price_unit')
    def _compute_base_price(self):
        for res in self:
            if not res.base_price and not res.update_base:
                res.base_price = res.price_unit
                res.update_base = True

    @api.depends('price_unit', 'base_price')
    def _compute_cost_saving(self):
        for res in self:
            res.cost_saving = res.base_price - res.price_unit

    @api.depends('product_id','product_template_id','price_unit','product_qty','cost_saving','base_price')
    def _compute_cost_savings(self):
        res = super(PurchaseOrderLine, self)._compute_cost_savings()
        for i in self:
            if i.order_id.agreement_id:
                if i.base_price:
                    cost_saving_percentage = (i.cost_saving / i.base_price) * 100
                    if cost_saving_percentage < 0:
                        i.cost_saving_percentage = 0
                    else:
                        i.cost_saving_percentage = cost_saving_percentage
                else:
                    i.cost_saving_percentage = 0
        return res