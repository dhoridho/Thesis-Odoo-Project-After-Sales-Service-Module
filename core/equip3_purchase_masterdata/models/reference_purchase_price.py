from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError

class ProductReferencePurchasePrice(models.Model):
    _name = "reference.purchase.price"
    _description = "Product Reference Purchase Price"

    name = fields.Char(string='Name')
    branch_id = fields.Many2one('res.branch', "Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    product_id = fields.Many2one('product.product', string='Product Variant', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, domain="[('purchase_ok','=',True)]")
    available_product_id = fields.Many2one('product.template', string='Product', required=True, compute="_compute_available_product_ids")
    reference_purchase_price = fields.Float('Reference Purchase Price', required=True)
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company.id, index=1)
    state = fields.Selection([("draft", "Draft"),
                              ("active", "Active"),
                              ("expired", "Expired"),
                              ("cancel", "Cancelled")
                              ], string='State', default="draft")
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True)

    @api.constrains('reference_purchase_price')
    def _check_Price(self):
        for record in self:
            if record.reference_purchase_price <= 0.00:
                raise ValidationError("Price must be entered")

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end < record.date_start:
                raise ValidationError("End Date should be greater then Start Date.")

    def action_confirm(self):
        return self.write({'state': 'active'})

    def action_cancel(self):
        return self.write({'state': 'cancel'})

    @api.model
    def _product_reference_price_list_expire(self):
        today_date = datetime.today()
        product_reference_purchase_price_ids = self.env['reference.purchase.price'].search([('date_end', '!=', False), ('date_end', '<', today_date)])
        product_reference_purchase_price_ids.write({'state': 'expired'})

    @api.model
    def create(self, vals):
        if vals['date_start'] != False and vals['date_end'] != False:
            res_data = self.env['reference.purchase.price'].search([
                ('state','in',('draft','active')),('company_id', '=', vals['company_id']), ('product_id', '=', vals['product_id']), ('product_tmpl_id', '=', vals['product_tmpl_id']), ('date_start', '!=', False), ('date_end', '!=', False)
            ])
            date_start = datetime.strptime(vals['date_start'], '%Y-%m-%d').date()
            date_end = datetime.strptime(vals['date_end'], '%Y-%m-%d').date()
            res_data = res_data.filtered(lambda x: (x.date_start <= date_start and x.date_end >= date_start) or (x.date_start <= date_end and x.date_end >= date_end))
            if res_data:
                raise ValidationError('There is the same Reference Purchase Price!')
        else:
            res_data = self.env['reference.purchase.price'].search([
                ('state','in',('draft','active')),('company_id', '=', vals['company_id']), ('product_id', '=', vals['product_id']), ('product_tmpl_id', '=', vals['product_tmpl_id'])
            ])
            if res_data:
                raise ValidationError('There is the same Reference Purchase Price!')
        res = super().create(vals)
        res.name = 'Reference Price - %s' % res.product_tmpl_id.name
        return res

    @api.onchange('product_tmpl_id')
    def onchange_product_id(self):
        if self.product_tmpl_id:
            partner_delivery_ids = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)], limit=1).ids
            if partner_delivery_ids:
                self.product_id = partner_delivery_ids[0]
            else:
                self.product_id = ""
