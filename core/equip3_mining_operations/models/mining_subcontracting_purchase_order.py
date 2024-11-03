from odoo import api, fields, models, _
from itertools import groupby
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import ValidationError, UserError


class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    mining_subcontracting = fields.Boolean(string=' Mining Subcontracting?', default=False)
    mining_site_id = fields.Many2one(comodel_name='mining.site.control', string='Mining Site')
    operation_id = fields.Many2one(comodel_name='mining.production.conf', string='Operation', required=True, domain="[('site_id', '=', mining_site_id), ('is_subcontracting', '=', True)]")
    operation_two_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', related='operation_id.operation_id', store=True, readonly=False)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    show_analytic_tags = fields.Boolean(string=' Show Analytic Tag?')

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    duration = fields.Float(string='Duration', compute='_compute_mining_duration')
    
    period_start = fields.Date(string='Period')
    period_end = fields.Date(string='Period End')
    period_start_max = fields.Date(string='Period Max')
    period_end_max = fields.Date(string='Period End Max')
    mining_actualization_ids = fields.Many2many(comodel_name='mining.production.actualization', string='Actualization', domain="[('period_from', '>=', period_start), ('period_to', '<=', period_end), ('operation_id', '=', operation_two_id), ('is_bills', '=', False)]")
    custom_total_qty = fields.Float(string='Total Quantity')
    custom_inv_count = fields.Integer(string='Inv Count', compute='_compute_custom_inv_count')
    
    def action_custom_open_bills(self):
        return {
            'name': "Bills",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('invoice_origin', '=', self.name)],
            'target': 'current',
        }
    
    def action_custom_crate_bill_view(self):
        self.write({
            'period_start': None,
            'period_end': None,
            'mining_actualization_ids': None,
            'custom_total_qty': 0
        })
        self.ensure_one()
        form_id = self.env.ref('equip3_mining_operations.purchase_order_custom_create_bills_view_form')
        return {
            'name': 'Create Bills',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'view_id': form_id.id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new'
        }
        
    def action_custom_create_bills(self):
        """Create the invoice associated to the PO.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if not self.period_start_max and not self.period_end_max:
            self.write({
                'period_start_max': self.period_start,
                'period_end_max': self.period_end
            })

        today = fields.Date.today()
        
        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            if today > order.period_end_max:
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            
            if order.mining_actualization_ids:
                for act in order.mining_actualization_ids:
                    act.write({'is_bills': True})
                    # for line_act in act.stock_valuation_layer_ids:
                    #     if line_act.product_id.categ_id.property_valuation != 'real_time':
                    #         raise ValidationError(_('Set category of product %s to Automated first!' % line_act.product_id.display_name))

                    #     account_id = line_act.product_id.categ_id.property_stock_valuation_account_id.id
                    #     name = '%s-  %s' % (self.name, line_act.product_id.display_name)
                    #     invoice_vals['invoice_line_ids'].append([0, 0, {
                    #         'account_id': account_id,
                    #         'name': name,
                    #         'debit': 0.0,
                    #         'credit': abs(line_act.value),
                    #         'quantity': self.custom_total_qty,
                    #     }])
                    #     invoice_vals['invoice_line_ids'].append([0, 0, {
                    #         'account_id': account_id,
                    #         'name':  name,
                    #         'debit': abs(line_act.value),
                    #         'credit': 0.0,
                    #         'quantity': self.custom_total_qty,
                    #     }])
                        
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_custom_account_move_line()))
                        pending_section = None
                invoice_line_vals = line._prepare_custom_account_move_line()
                invoice_line_vals.update({
                    'quantity': self.custom_total_qty,
                    'price_unit': (line.price_unit * self.custom_total_qty),
                })
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))
                        
            invoice_vals_list.append(invoice_vals)

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        return self.action_view_invoice(moves)
        
    def _compute_custom_inv_count(self):
        for rec in self:
            rec.custom_inv_count = self.env['account.move'].search_count([('invoice_origin', '=', rec.name)])
    
    @api.depends('start_date', 'end_date')
    def _compute_mining_duration(self):
        for rec in self:
            duration = 0
            if rec.start_date and rec.end_date:
                duration = (rec.end_date - rec.start_date).days
            rec.duration = duration
            
    @api.onchange('period_start', 'period_end')
    def _onchange_mining_actualization_ids(self):
        for rec in self:
            allowed_act = []
            qty = 0
            if rec.period_start and rec.period_end:
                act = self.env['mining.production.actualization'].search([('period_from', '>=', rec.period_start), 
                                                                          ('period_to', '<=', rec.period_end), 
                                                                          ('operation_id', '=', rec.operation_two_id.id),
                                                                          ('is_bills', '=', False)])
                if act:
                    for a in act:
                        allowed_act.append(a.id)
                        if a.operation_id.operation_type_id == 'shipment':
                            if a.delivery_ids:
                                for f in a.delivery_ids:
                                    qty += f.total_amount
                        else:
                            if a.output_ids:
                                for out in act.output_ids:
                                    qty += out.qty_done
            rec.write({
                'mining_actualization_ids': [(6, 0, allowed_act)],
                'custom_total_qty': qty
            })
            # rec.mining_actualization_ids = [(6, 0, allowed_act)]
            # rec.custom_total_qty = qty
            
    @api.onchange('mining_actualization_ids')
    def _onchange_custom_mining_actualization_ids(self):
        for rec in self:
            qty = 0
            if rec.mining_actualization_ids:
                for act in rec.mining_actualization_ids:
                    if act.operation_id.operation_type_id == 'shipment':
                        if act.delivery_ids:
                            for f in act.delivery_ids:
                                qty += f.total_amount
                    else:
                        if act.output_ids:
                            for out in act.output_ids:
                                qty += out.qty_done
            rec.write({
                'custom_total_qty': qty
            })
            # rec.custom_total_qty = qty
            

class InheritPOLine(models.Model):
    _inherit = 'purchase.order.line'

    cost_saving_percentage = fields.Float(string='Cost Saving Percentage')

    def _prepare_custom_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.order_id.custom_total_qty, # self.qty_to_invoice
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False) * self.order_id.custom_total_qty,
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'analytic_account_id': self.account_analytic_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'purchase_line_id': self.id,
        }
        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
        })
        return res