from odoo import fields, models, api, _ , tools
from odoo.exceptions import UserError     



class AccountMove(models.Model):
    _inherit = 'account.move'

        
    def action_confirm(self):
        if self.env.context.get('from_product_cost_adjustment'):
            return super(AccountMove, self).action_confirm()
        
        if self.move_type == 'in_invoice' and self.company_id.anglo_saxon_accounting:
        # if self.company_id.anglo_saxon_accounting:
            lines_to_confirm = []
            for line in self.invoice_line_ids:
                if line.product_id.product_tmpl_id.categ_id.property_valuation == 'real_time' :
                    lines_to_confirm.append(line)
            # state_po_reference = self.po_reference_ids.mapped('state')
            # state_ro_reference = self.ro_reference_ids.mapped('state')
            
            # if state_ro_reference == ['draft']:
            #     for line in self.invoice_line_ids:
            #         if line.product_id.product_tmpl_id.categ_id.property_valuation == 'real_time' and line.product_id.product_tmpl_id.purchase_method == 'purchase':
            #             lines_to_confirm.append(line)
            # else:
            #     for line in self.invoice_line_ids:
            #         if line.product_id.product_tmpl_id.categ_id.property_valuation == 'real_time' and line.product_id.product_tmpl_id.purchase_method == 'receive':
            #             lines_to_confirm.append(line)

            if lines_to_confirm:
                # Create records in product.cost.adjustment model
                adjustment_lines = []
                for line in lines_to_confirm:
                    adjustment_lines.append((0, 0, {
                        'currency_id': line.currency_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'tax_ids': line.tax_ids.ids,
                        'price_subtotal': line.price_subtotal,
                        'move_id': self.id,
                    }))
                adjustment = self.env['product.cost.adjustment'].create({
                    'adjustment_line_ids': adjustment_lines,
                })
                # Show the wizard
                return {
                    'name': _('Product Cost Adjustment Confirmation'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'product.cost.adjustment',
                    'view_mode': 'form',
                    'res_id': adjustment.id,
                    'target': 'new',
                    'context': {'from_product_cost_adjustment': True},
                }

        return super(AccountMove, self).action_confirm()


    def action_request_for_approval(self):
        if self.env.context.get('from_product_cost_adjustment'):
            return super(AccountMove, self).action_request_for_approval()
        
        if self.move_type == 'in_invoice' and self.company_id.anglo_saxon_accounting:
        # if self.company_id.anglo_saxon_accounting:
            lines_to_confirm = []
            for line in self.invoice_line_ids:
                if line.product_id.product_tmpl_id.categ_id.property_valuation == 'real_time':
                    lines_to_confirm.append(line)
            if lines_to_confirm:
                # Create records in product.cost.adjustment model
                adjustment_lines = []
                for line in lines_to_confirm:
                    adjustment_lines.append((0, 0, {
                        'currency_id': line.currency_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'tax_ids': line.tax_ids.ids,
                        'price_subtotal': line.price_subtotal,
                        'move_id': self.id,
                    }))
                adjustment = self.env['product.cost.adjustment'].create({
                    'adjustment_line_ids': adjustment_lines,
                })
                # Show the wizard
                return {
                    'name': _('Product Cost Adjustment Confirmation'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'product.cost.adjustment',
                    'view_mode': 'form',
                    'res_id': adjustment.id,
                    'target': 'new',
                    'context': {'from_product_cost_adjustment': True},
                }

        return super(AccountMove, self).action_request_for_approval()
            
    
    # def product_cost_adjusment(self):
    #     lines_to_confirm = []
    #     for line in self.invoice_line_ids:
    #         # if self.move_type == 'out_invoice' and line.product_id.product_tmpl_id.purchase_method == 'purchase'\
    #         #     and line.product_id.product_tmpl_id.categ_id.property_valuation == 'real_time':
    #         #      lines_to_confirm.append(line)
    #         if line.product_id.product_tmpl_id.categ_id.property_valuation == 'real_time':
    #             lines_to_confirm.append(line)
    #     if lines_to_confirm:
    #         # Create records in product.cost.adjustment model
    #         adjustment_lines = []
    #         for line in lines_to_confirm:
    #             adjustment_lines.append((0, 0, {
    #                 'currency_id': line.currency_id.id,
    #                 'product_id': line.product_id.id,
    #                 'quantity': line.quantity,
    #                 'price_unit': line.price_unit,
    #                 'move_id': self.id,
    #             }))
    #         adjustment = self.env['product.cost.adjustment'].create({
    #             'adjustment_line_ids': adjustment_lines,
    #         })
    #         # Show the wizard
    #         return {
    #             'name': _('Product Cost Adjustment Confirmation'),
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'product.cost.adjustment',
    #             'view_mode': 'form',
    #             'res_id': adjustment.id,
    #             'target': 'new',
            # }