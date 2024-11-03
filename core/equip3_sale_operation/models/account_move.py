
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json

class AccountMove(models.Model):
    _inherit = 'account.move'

    # branch_id = fields.Many2one(
    #     'res.branch',
    #     default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
    #     related="",
    #     readonly=False)
    sale_order_reference_id = fields.Many2one('sale.order', string="Sale Order Reference")
    filter_sale_order_reference_ids = fields.Char(string='Sale Order Reference', compute='_get_filter_sale_order', store=False)
    is_dp = fields.Boolean("Is Down Payment")
    is_recurring = fields.Boolean("Is Recurring")

    @api.depends('move_type', 'partner_id','branch_id')
    def _compute_sale_order(self):
        for record in self:
            order_ids = []
            if record.move_type == 'out_invoice' and record.partner_id and record.branch_id:
                sale_order_ids = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', '=', 'sale'),
                    ('branch_id','=',record.branch_id.id)
                ])
                move_ids = self.search([('state', '=', 'posted')])
                move_sale_order_ids = move_ids.mapped('sale_order_ids').ids
                order_ids = sale_order_ids.filtered(lambda r: r.id not in move_sale_order_ids).ids
            record.filter_sale_order_ids = [(6, 0, order_ids)]

    @api.onchange('sale_order_ids', 'purchase_order_ids', 'picking_ids')
    def _change_invoice_lines(self):
        data = []
        sale_order_ids = self.sale_order_ids and self.sale_order_ids.ids or []
        purchase_order_ids = self.purchase_order_ids and self.purchase_order_ids.ids or []
        if self.move_type == 'out_invoice':
            if self.sale_order_ids and not self.picking_ids:
                self.line_ids = False
                for lines in self.sale_order_ids.order_line:
                    if lines.product_id.invoice_policy == 'order':
                        data.append((0, 0, {
                            'product_id': lines.product_id.id,
                            'quantity': lines.product_uom_qty - lines.qty_invoiced,
                            'discount_method': lines.discount_method,
                            'discount_amount': lines.discount_amount,
                            'price_unit': lines.price_unit,
                            'price_total': lines.price_total,
                            'tax_ids': [(6, 0, lines.tax_id.ids)],
                            "price_subtotal": lines.price_subtotal,
                            'analytic_tag_ids': [(6, 0, lines.order_id.account_tag_ids.ids)],
                        }))
                    else:
                        if lines.qty_delivered > 0:
                            data.append((0, 0, {
                                'product_id': lines.product_id.id,
                                'quantity': lines.qty_delivered - lines.qty_invoiced,
                                'discount_method': lines.discount_method,
                                'discount_amount': lines.discount_amount,
                                'price_unit': lines.price_unit,
                                'price_total': lines.price_total,
                                'tax_ids': [(6, 0, lines.tax_id.ids)],
                                "price_subtotal": lines.price_subtotal,
                                'analytic_tag_ids': [(6, 0, lines.order_id.account_tag_ids.ids)],
                            }))
            elif self.sale_order_ids and self.picking_ids:
                self.line_ids = False
                for lines in self.picking_ids.mapped('move_ids_without_package'):
                    if lines.sale_line_id.qty_delivered <= 0:
                        raise ValidationError("There’s product with delivered quantity is 0 so the product won’t be shown at invoice lines.")
                    if lines.product_id.invoice_policy == 'order':
                        data.append((0, 0, {
                            'product_id': lines.product_id.id,
                            'quantity': lines.product_uom_qty,
                            'price_unit': lines.sale_line_id.price_unit,
                            'price_total': lines.sale_line_id.price_total,
                            "price_subtotal": lines.sale_line_id.price_subtotal,
                            'analytic_tag_ids': [(6, 0, lines.sale_line_id.order_id.account_tag_ids.ids)],
                        }))
                    else:
                        if lines.quantity_done > 0:
                            data.append((0, 0, {
                                'product_id': lines.product_id.id,
                                'quantity': lines.quantity_done,
                                'price_unit': lines.sale_line_id.price_unit,
                                'price_total': lines.sale_line_id.price_total,
                                "price_subtotal": lines.sale_line_id.price_subtotal,
                                'analytic_tag_ids': [(6, 0, lines.sale_line_id.order_id.account_tag_ids.ids)],
                            }))
        elif self.move_type == "in_invoice":
            if self.purchase_order_ids and not self.picking_ids:
                self.line_ids = False
                for lines in self.purchase_order_ids.order_line:
                    if lines.product_id.purchase_method == 'purchase':
                        data.append((0, 0, {
                            'product_id': lines.product_id.id,
                            'quantity': lines.product_qty-lines.qty_invoiced,
                            'discount_method': lines.discount_method,
                            'discount_amount': lines.discount_amount,
                            'price_unit': lines.price_unit,
                            'price_total': lines.price_total,
                            "price_subtotal": lines.price_subtotal,
                            'analytic_tag_ids': [(6, 0, lines.order_id.analytic_account_group_ids.ids)],
                            'purchase_line_id' : lines._origin.id,
                        }))
                    else:
                        if lines.qty_received > 0:
                            data.append((0, 0, {
                                'product_id': lines.product_id.id,
                                'quantity': lines.qty_received-lines.qty_invoiced,
                                'discount_method': lines.discount_method,
                                'discount_amount': lines.discount_amount,
                                'price_unit': lines.price_unit,
                                'price_total': lines.price_total,
                                "price_subtotal": lines.price_subtotal,
                                'analytic_tag_ids': [(6, 0, lines.order_id.analytic_account_group_ids.ids)],
                                'purchase_line_id' : lines._origin.id,
                            }))
            elif self.purchase_order_ids and self.picking_ids:
                self.line_ids = False
                for lines in self.picking_ids.mapped('move_ids_without_package'):
                    if lines.purchase_line_id.qty_received <= 0:
                        raise ValidationError("There’s product with delivered quantity is 0 so the product won’t be shown at bill lines.")
                    if lines.product_id.purchase_method == 'purchase':
                        data.append((0, 0, {
                            'product_id': lines.product_id.id,
                            'quantity': lines.product_uom_qty,
                            'price_unit': lines.purchase_line_id.price_unit,
                            'price_total': lines.purchase_line_id.price_total,
                            "price_subtotal": lines.purchase_line_id.price_subtotal,
                            'analytic_tag_ids': [(6, 0, lines.purchase_line_id.order_id.analytic_account_group_ids.ids)],
                        }))
                    else:
                        if lines.quantity_done > 0:
                            data.append((0, 0, {
                                'product_id': lines.product_id.id,
                                'quantity': lines.quantity_done,
                                'price_unit': lines.purchase_line_id.price_unit,
                                'price_total': lines.purchase_line_id.price_total,
                                "price_subtotal": lines.purchase_line_id.price_subtotal,
                                'analytic_tag_ids': [(6, 0, lines.purchase_line_id.order_id.analytic_account_group_ids.ids)],
                            }))        
        # self.discount_type = 'line'
        self.invoice_line_ids = data
        self.purchase_order_ids = purchase_order_ids
        if not sale_order_ids:
            for line in self.invoice_line_ids:
                line._onchange_product_id()
        self.line_ids._onchange_price_subtotal()
        self._recompute_dynamic_lines(recompute_all_taxes=True)

    @api.depends('company_id')
    def _get_filter_sale_order(self):
        sale_order = []
        for record in self:
            sale_order_ids = record.env['sale.order'].search([('sale_state', '=', 'in_progress'),('invoice_ids','=',False)])
            record.filter_sale_order_reference_ids = json.dumps([('id', 'in', sale_order_ids.ids)])

    @api.onchange('sale_order_reference_id')
    def get_sale_order_reference(self):
        name = self.sale_order_reference_id.name
        if self.sale_order_reference_id:
            self.invoice_line_ids = False
            self.line_ids = False
            sale_order_line = []
            fiscal_position = self.sale_order_reference_id.fiscal_position_id
            for order_line in self.sale_order_reference_id.order_line:
                accounts = order_line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
                vals = order_line._prepare_invoice_line()
                vals.update({
                    'account_id': accounts['income'].id, 
                    'quantity' : order_line.product_uom_qty,
                    'price_tax': order_line.price_tax,
                    'price_subtotal': order_line.price_subtotal,
                    'sale_line_ids': [(6, 0, order_line.ids)]
                })
                sale_order_line.append((0, 0, vals))
            customer_reference = name + ("-") + self.sale_order_reference_id.partner_id.name
            self.update({'partner_id': self.sale_order_reference_id.partner_id.id,
                        'invoice_payment_term_id' : self.sale_order_reference_id.payment_term_id.id,
                        'branch_id' : self.sale_order_reference_id.branch_id.id,
                        'partner_shipping_id' : self.sale_order_reference_id.partner_shipping_id.id,
                        'invoice_line_ids' : sale_order_line,
                        'move_type': 'out_invoice',
                        'invoice_user_id' : self.sale_order_reference_id.user_id.id,
                        'team_id' : self.sale_order_reference_id.team_id.id,
                        'fiscal_position_id' : self.sale_order_reference_id.fiscal_position_id.id,
                        'ref' : customer_reference,
                         'discount_amt': self.sale_order_reference_id.discount_amt,
                         'discount_method': self.sale_order_reference_id.discount_method,
                         'discount_amount': self.sale_order_reference_id.discount_amount,
                        })
            self._onchange_invoice_line_ids()
            total = 0
            for line in self.invoice_line_ids:
                journal_filter_line = self.line_ids.filtered(lambda r:r.account_id.id == line.account_id.id)
                journal_filter_line.credit = line.price_unit
                total += line.price_unit
            partner_filter_line = self.line_ids.filtered(lambda r:r.account_id.id == self.partner_id.property_account_receivable_id.id)
            partner_filter_line.debit = total
        else:
            self.update({'partner_id': False,
                        'invoice_payment_term_id' : False,
                        'partner_shipping_id' : False,
                        'invoice_line_ids' : False,
                        'line_ids': False,
                        # 'invoice_user_id' : False,
                        # 'team_id' : False,
                        'fiscal_position_id' : False,
                        'ref' : False  
                        })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(AccountMove, self).create(vals_list)
        for line in lines:
            if line.sale_order_reference_id:
                line.message_post(body=(_("This journal entry has been created from : %s") % [l.name for l in line.sale_order_ids]))
                # membuat perhitungan qty invoiced salah jika tidak single delivery date / delivery address
                # for invoice_line in line.invoice_line_ids:
                #     filter_order_line = line.sale_order_reference_id.order_line.filtered(lambda r:r.product_id.id == invoice_line.product_id.id and r.multiple_do_date_new == invoice_line. and r.line_warehouse_id_new.id == invoice_line)
                #     if filter_order_line:
                #         invoice_line.sale_line_ids = [(6, 0, filter_order_line[0].ids)]
            if line.sale_order_ids:
                line.message_post(body=(_("This journal entry has been created from : %s") % [l.name for l in line.sale_order_ids]))
                # membuat perhitungan qty invoiced salah jika tidak single delivery date / delivery address
                # for invoice_line in line.invoice_line_ids:
                #     filter_order_line = line.sale_order_ids.order_line.filtered(lambda r:r.product_id.id == invoice_line.product_id.id)
                #     if filter_order_line:
                #         invoice_line.sale_line_ids = [(6, 0, filter_order_line[0].ids)]
        return lines

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_line_ids = fields.Many2many(
        'sale.order.line',
        'sale_order_line_invoice_rel',
        'invoice_line_id', 'order_line_id',
        string='Sales Order Lines', readonly=False, copy=False)