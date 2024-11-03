from odoo import api , fields , models


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    customer_credit_limit = fields.Float('Customer Available Credit Limit', compute="_compute_customer_credit_limit", tracking=True)
    total_sale_order_cons = fields.Integer(compute='_compute_total_sale_order_cons', string='Sales Const')
    sale_order_const_ids = fields.One2many('sale.order.const', 'partner_id', 'Sales Order')
    
    def _compute_total_sale_order_cons(self):
        for rec in self:
            sale_order_count = self.env['sale.order.const'].search_count([('partner_id', '=', self.name)])
            rec.total_sale_order_cons = sale_order_count

    def action_sale_order_cons(self):
        return {
            'name': ("Sales Construction"),
            'view_mode': 'tree,form',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('partner_id', '=', self.id)],
        }


    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.state', 'invoice_ids.amount_residual', 'sale_order_ids', 'sale_order_ids.amount_total', 'sale_order_ids.state', 'cust_credit_limit',
                  'sale_order_const_ids', 'sale_order_const_ids.amount_total', 'sale_order_const_ids.state')
    def _compute_customer_credit_limit(self):
        for record in self:
            sale_ids = record.sale_order_ids.filtered(lambda l: l.state == 'sale' and l.over_limit_approved == False and l.invoice_status in ('to invoice', 'no'))
            amount_value = sum(sale_ids.mapped('amount_total'))
            invoice_id = record.invoice_ids.filtered(lambda l: l.project_invoice == False and l.payment_state in ('not_paid', 'in_payment', 'partial'))
            amount_total_value = sum(invoice_id.mapped('amount_total'))
        
            #construction
            sale_const = record.sale_order_const_ids.filtered(lambda l: l.state == 'sale')
            amount_value_const = sum(sale_const.mapped('amount_total'))
            invoice_id_const = record.invoice_ids.filtered(lambda l: l.project_invoice == True and l.payment_state in ('not_paid', 'in_payment', 'partial', 'paid'))
            amount_invoice_const = sum(invoice_id_const.mapped('amount_total'))
            amount_residual_const = sum(invoice_id_const.mapped('amount_residual'))
            construction_credit_limit = amount_value_const - (amount_invoice_const - amount_residual_const)
            
            #all
            customer_credit = record.cust_credit_limit - ( amount_value + amount_total_value + construction_credit_limit)
            record.customer_credit_limit = customer_credit

  