from odoo import models, fields, api, _


class Agreement(models.Model):
    _inherit = 'agreement'

    expected_revenue = fields.Float(string='Expected Revenue')
    expected_cost = fields.Float(string='Expected Cost')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,default=lambda self: self.env.company.currency_id.id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all_material', tracking=True)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all_material')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all_material')
    
    @api.depends('line_ids.price_total')
    def _amount_all_material(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                line._compute_amount_price()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

class AgreementLine(models.Model):
    _inherit = 'agreement.line'

    unit_price = fields.Float(string='Unit Price', digits='Product Price', compute='compute_unit_price')
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)
    price_subtotal = fields.Monetary(compute='_compute_amount_price', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount_price', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount_price', string='Tax', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,default=lambda self: self.env.company.currency_id.id)
    
    @api.depends('product_id')
    def compute_unit_price(self):
        for line in self:
            if line.product_id:
                line.unit_price = line.product_id.lst_price
            else:
                line.unit_price = 0.0
                
    @api.depends('qty', 'unit_price', 'taxes_id')
    def _compute_amount_price(self):
        for line in self:
            taxes = line.taxes_id.compute_all(
                line.unit_price,
                line.agreement_id.currency_id,
                line.qty,)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

AgreementLine()