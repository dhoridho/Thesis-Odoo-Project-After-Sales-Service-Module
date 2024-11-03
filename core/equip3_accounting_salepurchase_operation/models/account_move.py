from odoo import tools, models, fields, api, _ 
from odoo.exceptions import UserError, ValidationError
import sys, json, copy
from operator import itemgetter
sys.setrecursionlimit(10000)

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_po_reference(self):
        domain = []
        if self.move_type == 'in_invoice':
            domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'purchase'), ('invoice_status', '=', 'to invoice'), ('is_services_orders','!=',True), ('branch_id','=',self.branch_id.id)]


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    sale_order_ids = fields.Many2many('sale.order', string="Sale Order Reference")
    filter_sale_order_ids = fields.Char('sale.order', compute='_compute_sale_order', store=False)
    purchase_order_ids = fields.Many2many('purchase.order', string="Purchase Order Reference")
    filter_purchase_order_ids = fields.Char('purchase.order', compute='_compute_purchase_order', store=False)
    picking_ids = fields.Many2many('stock.picking')
    filter_picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', store=False)
    sale_order_ids_boolean = fields.Boolean(default=True)
    purchase_order_ids_boolean = fields.Boolean(default=True)
    picking_ids_boolean = fields.Boolean(default=True)
    is_clear_purchase_order_ids = fields.Boolean(default=False)
    po_reference_ids = fields.Many2many('purchase.order', string='Purchase Order Reference', relation='account_move_po_reference_rel')
    ro_reference_ids = fields.Many2many('stock.picking', string='Receipt Order Reference', relation='account_move_ro_reference_rel')


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id:
                if rec.move_type == 'in_invoice':
                    rec.purchase_order_ids = [(5, 0, 0)]  # Clear existing purchase orders
                    rec.picking_ids = [(5, 0, 0)]  # Clear existing pickings

                else:
                    rec.sale_order_ids = [(5, 0, 0)]
                    rec.picking_ids = [(5, 0, 0)]

            else:
                rec.sale_order_ids = [(5, 0, 0)]
                rec.purchase_order_ids = [(5, 0, 0)]  # Clear existing purchase orders
                rec.picking_ids = [(5, 0, 0)]  # Clear existing pickings
                
    @api.onchange('sale_order_ids')
    def _onchange_sale_order_ids(self):
        for rec in self:
            if rec.sale_order_ids:
                rec.purchase_order_ids = False
                rec.picking_ids = False
                picking_ids = []
                for order in rec.sale_order_ids:
                    picking_ids += order.picking_ids.ids
                rec.picking_ids = [(6, 0, picking_ids)]
            else:
                # rec.sale_order_ids = False
                rec.picking_ids = False
                rec.invoice_line_ids = False

    # @api.onchange('purchase_order_ids')
    # def _onchange_purchase_order_ids(self):
    #     for rec in self:
    #         if rec.purchase_order_ids:
    #             rec.sale_order_ids = False
    #             rec.picking_ids = False
    #             picking_ids = []
    #             for order in rec.purchase_order_ids:
    #                 picking_ids += order.picking_ids.ids
    #             rec.picking_ids = [(6, 0, picking_ids)]
    #         else:
    #             rec.purchase_order_ids = False
    #             rec.picking_ids = False

    @api.onchange('po_reference_ids')
    def _onchange_po_reference_ids(self):
        for rec in self:
            if rec.po_reference_ids:
                rec.sale_order_ids = False
                rec.purchase_order_ids = rec.po_reference_ids
                rec.picking_ids = False
                picking_ids = []
                invoice_lines = []
                
                for order in rec.po_reference_ids:
                    picking_ids += order.picking_ids.ids
                    for line in order.order_line:
                        invoice_lines.append((0, 0, {
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'quantity': line.product_qty,
                            'price_unit': line.price_unit,
                            'tax_ids': [(6, 0, line.taxes_id.ids)],
                            'account_id': line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id,
                        }))
                
                rec.ro_reference_ids = [(6, 0, picking_ids)]
                rec.picking_ids = [(6, 0, picking_ids)]
                rec.invoice_line_ids = [(5, 0, 0)] + invoice_lines

            else:
                rec.purchase_order_ids = False
                rec.picking_ids = False
                rec.ro_reference_ids = False
                rec.invoice_line_ids = False

    @api.onchange('ro_reference_ids')
    def _onchange_ro_reference_ids(self):
        for rec in self:
            if rec.ro_reference_ids:
                po_ids = rec.ro_reference_ids.mapped('purchase_id')
                rec.po_reference_ids = [(6, 0, po_ids.ids)]
                rec.purchase_order_ids = rec.po_reference_ids
                rec.picking_ids = rec.ro_reference_ids
            else:
                rec.po_reference_ids = False
                rec.purchase_order_ids = False
                rec.picking_ids = False
                rec.invoice_line_ids = False

    @api.onchange('picking_ids')
    def _onchange_picking_ids(self):
        for rec in self:
            if rec.picking_ids:
                if rec.move_type == 'out_invoice':
                    so_ids = rec.picking_ids.mapped('sale_id')
                    rec.sale_order_ids = [(6, 0, so_ids.ids)]
                if rec.move_type == 'in_invoice':
                    po_ids = rec.picking_ids.mapped('purchase_id')
                    rec.purchase_order_ids = [(6, 0, po_ids.ids)]

            else:
                rec.sale_order_ids = False
                rec.purchase_order_ids = False
                rec.invoice_line_ids = False


    @api.onchange('sale_order_ids', 'purchase_order_ids', 'picking_ids')
    def onchange_field_sale_purchase(self):
        for rec in self:
            if len(rec.sale_order_ids) == 0 and len(rec.picking_ids) == 0 and len(rec.purchase_order_ids) == 0:
                rec.sale_order_ids_boolean = True
                rec.purchase_order_ids_boolean = True
                rec.picking_ids_boolean = True
                # rec.picking_ids = False
            else:
                if rec.sale_order_ids:
                    rec.sale_order_ids_boolean = True
                    rec.purchase_order_ids_boolean = False
                    rec.picking_ids_boolean = False

                if rec.purchase_order_ids:
                    rec.sale_order_ids_boolean = False
                    rec.purchase_order_ids_boolean = True
                    rec.picking_ids_boolean = False

                if rec.picking_ids:
                    rec.sale_order_ids_boolean = False
                    rec.purchase_order_ids_boolean = False
                    rec.picking_ids_boolean = True

 
    @api.onchange('sale_order_ids', 'purchase_order_ids', 'picking_ids')
    def _change_invoice_lines(self):
        res = super(AccountMove, self)._change_invoice_lines()
        for rec in self:
            if rec.picking_ids and not rec.sale_order_ids:
                rec.line_ids = False
                data = []
                purchase_order_ids = []
                for lines in rec.picking_ids.mapped('move_ids_without_package'):
                    purchase_order = False
                    sale_order = False
                    if lines.purchase_line_id:
                        purchase_order = lines.purchase_line_id
                        if lines.purchase_line_id.order_id not in purchase_order_ids:
                            purchase_order_ids.append(lines.purchase_line_id.order_id)
                    if lines.sale_line_id:
                        sale_order = lines.sale_line_id
                    for order_id in purchase_order_ids:
                        rec.write({
                            'purchase_order_ids': [(4, order_id.id)],
                            'tax_applies_on': order_id.tax_discount_policy,
                            'discount_type': order_id.discount_type,
                            'discount_method': order_id.discount_method,
                            'multi_discount': order_id.multi_discount,
                            'discount_amount': order_id.discount_amount,
                            'branch_id': order_id.branch_id.id,
                            'invoice_date': fields.date.today(),
                            'amount_tax': order_id.amount_tax
                        })
                    if rec.move_type == 'in_invoice':
                        tmp_data = {}
                        if lines.product_id.purchase_method == 'purchase':
                            tmp_data = {
                                'product_id': purchase_order.product_id.id if purchase_order else lines.product_id.id,
                                'quantity':  purchase_order.product_qty if purchase_order else lines.product_qty,
                                'purchase_line_id' : purchase_order.id if purchase_order else False,
                                'product_uom_id': purchase_order.product_uom.id if purchase_order else lines.product_uom.id,
                            }
                        else:
                            if lines.quantity_done > 0:
                                tmp_data = {
                                    'product_id': purchase_order.product_id.id if purchase_order else lines.product_id.id,
                                    'quantity':  purchase_order.product_qty if purchase_order else lines.quantity_done,
                                    'purchase_line_id' : purchase_order.id if purchase_order else False,
                                    'product_uom_id': purchase_order.product_uom.id if purchase_order else lines.product_uom.id,
                                }
                        if purchase_order:
                            tmp_data['price_tax'] = purchase_order.price_tax
                            tmp_data['price_unit'] = purchase_order.price_unit
                            tmp_data['price_total'] = purchase_order.price_total
                            tmp_data['price_subtotal'] = purchase_order.price_subtotal
                            tmp_data['discount_method'] = purchase_order.discount_method
                            tmp_data['multi_discount'] = purchase_order.multi_discount
                            tmp_data['discount_amount'] = purchase_order.discount_amount
                            tmp_data['discount_amt'] = purchase_order.discounted_value
                        data.append((0, 0, tmp_data))
                    else:
                        tmp_data = {}
                        if lines.product_id.invoice_policy == 'order':
                            tmp_data = {
                                'product_id': lines.product_id.id,
                                'quantity': lines.product_uom_qty,
                                'purchase_line_id' : purchase_order.id if purchase_order else False,
                            }

                        else:
                            if lines.quantity_done > 0:
                                tmp_data = {
                                    'product_id': lines.product_id.id,
                                    'quantity': lines.quantity_done,
                                    'purchase_line_id' : purchase_order.id if purchase_order else False,
                                }
                        if sale_order:
                            tmp_data['price_unit'] = sale_order.price_unit
                            tmp_data['price_total'] = sale_order.price_total
                            tmp_data['price_subtotal'] = sale_order.price_subtotal
                        data.append((0, 0, tmp_data))
                rec.invoice_line_ids = data
            for line in rec.invoice_line_ids:
                line.name = line._get_computed_name()
                line.account_id = line._get_computed_account()
                line.analytic_tag_ids = rec.analytic_group_ids
                taxes = line._get_computed_taxes()
                if taxes and line.move_id.fiscal_position_id:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes, partner=rec.partner_id)
                line.tax_ids = taxes
                if not rec.purchase_order_ids:
                    line._onchange_price_subtotal()
            rec._recompute_dynamic_lines(recompute_all_taxes=True)


    # def _compute_amount(self):
    #     res = super(AccountMove, self)._compute_amount()
    #     for rec in self:
    #         rec.subtotal_amount = sum(line.price_unit * line.quantity for line in rec.invoice_line_ids if not line.is_down_payment)
    #         rec.amount_untaxed = sum(line.price_subtotal for line in rec.invoice_line_ids if not line.is_down_payment)
    #         rec.amount_tax = sum(line.price_tax for line in rec.invoice_line_ids)
    #         rec.amount_total = rec.amount_untaxed + rec.amount_tax + rec.down_payment_amount
    #         if rec.tax_applies_on == 'Before Discount':
    #             if rec.move_type == 'out_invoice':
    #                 if rec.discount_type == 'line':
    #                     if rec.discount_amount_line < 0:
    #                         rec.discount_amount_line * -1
    #                     rec.amount_total = (rec.amount_untaxed + rec.amount_tax + rec.down_payment_amount) - rec.discount_amount_line
    #                 else:
    #                     rec.amount_total = (rec.amount_untaxed + rec.amount_tax + rec.down_payment_amount) - rec.discount_amt
    #             else:
    #                 if rec.discount_type == 'line':
    #                     if rec.discount_amount_line < 0:
    #                         rec.discount_amount_line * -1
    #                     rec.amount_total = (rec.amount_untaxed + rec.amount_tax + rec.down_payment_amount) - rec.discount_amount_line
    #                 else:
    #                     rec.amount_total = (rec.amount_untaxed + rec.amount_tax + rec.down_payment_amount) - rec.discount_amt

    @api.depends('move_type', 'partner_id','branch_id')
    def _compute_sale_order(self):
        for record in self:
            order_ids = []
            if record.move_type == 'out_invoice' and record.partner_id and record.branch_id:
                sale_order_ids = self.env['sale.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', '=', 'sale'),
                    # ('invoice_status', '!=', 'invoiced'),
                    ('invoice_status', '=', 'to invoice'),
                    ('branch_id','=',record.branch_id.id)
                ])
                # move_ids = self.search([('state', '=', 'posted')])
                # move_sale_order_ids = move_ids.mapped('sale_order_ids').ids
                order_ids = sale_order_ids.ids
            record.filter_sale_order_ids = json.dumps([('id','in', order_ids)])

    @api.model_create_multi
    def create(self, vals_list):
        rslt = super(AccountMove, self).create(vals_list)
        for rec in rslt:
            if rec.purchase_order_ids:
                for lines in rec.purchase_order_ids.mapped('order_line'):
                    line_id = rec.invoice_line_ids.filtered(lambda r: r.product_id == lines.product_id)
                    if line_id:
                        # fixing untuk bug perhitungan 4330,5330 dan 6330 dikali 0.01
                        qty_invoiced = lines.qty_invoiced
                        res_qty_invoiced = lines.qty_invoiced * 10 / 10
                        if qty_invoiced != res_qty_invoiced:
                            qty_invoiced = res_qty_invoiced
                        if lines.product_id.purchase_method == 'purchase':
                            if qty_invoiced > lines.product_qty:
                                raise UserError('QTY Billed > Qty PO')
                        else:
                            if qty_invoiced > lines.qty_received:
                                raise UserError('QTY Billed > Qty received')
            if rec.sale_order_ids:
                for lines in rec.sale_order_ids.mapped('order_line'):
                    line_id = rec.invoice_line_ids.filtered(lambda r: r.product_id == lines.product_id)
                    if line_id:
                        if not lines.is_recurring:
                            if lines.product_id.invoice_policy == 'order':
                                if lines.qty_invoiced > lines.product_uom_qty:
                                    raise UserError('QTY Invoiced > Qty SO')
                            else:
                                if lines.qty_invoiced > lines.qty_delivered:
                                    raise UserError('QTY Invoiced > Qty Delivered')
            if rec.picking_ids:
                for res in rec.picking_ids:
                    for move in res.move_lines:
                        if move.purchase_line_id:
                            odred_line = move.purchase_line_id
                            line_id = rec.invoice_line_ids.filtered(lambda r: r.product_id == odred_line.product_id)
                            if line_id:
                                if odred_line.product_id.purchase_method == 'purchase':
                                    if odred_line.qty_invoiced > odred_line.product_qty:
                                        raise UserError('QTY Billed > Qty PO')
                                else:
                                    if odred_line.qty_invoiced > odred_line.qty_received:
                                        raise UserError('QTY Billed > Qty received')
                        if move.sale_line_id:
                            odred_line = move.sale_line_id
                            line_id = rec.invoice_line_ids.filtered(lambda r: r.product_id == odred_line.product_id)
                            if line_id:
                                if odred_line.product_id.invoice_policy == 'order':
                                    if not odred_line.is_recurring:
                                        if odred_line.qty_invoiced > odred_line.product_uom_qty:
                                            raise UserError('QTY Invoiced > Qty SO')
                                else:
                                    if not odred_line.is_recurring:
                                        if odred_line.qty_invoiced > odred_line.qty_delivered:
                                            raise UserError('QTY Invoiced > Qty Delivered')
        return rslt
    
    # Function _remove_stock_account_anglo_saxon_in_lines_vals() lebih ideal disimpan di tim sale purchase 
    # di module yg terdepedensi langsung dengan module purchase_stock atau yg punya depedensi dengan module tersebut, 
    # atau module yg terdepedensi langsung dengan Function _stock_account_prepare_anglo_saxon_in_lines_vals
    
    def _remove_stock_account_anglo_saxon_in_lines_vals(self):
        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund', 'in_receipt') or not move.company_id.anglo_saxon_accounting:
                continue
            if not move.sale_order_ids:
                continue
            move = move.with_company(move.company_id)
            for line in move.invoice_line_ids.filtered(lambda line: line.product_id.type == 'product' and line.product_id.valuation == 'real_time'):
                # Filter out lines being not eligible for price difference.
                if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    continue
                # Retrieve accounts needed to generate the price difference.
                debit_pdiff_account = line.product_id.property_account_creditor_price_difference or line.product_id.categ_id.property_account_creditor_price_difference_categ
                debit_pdiff_account = move.fiscal_position_id.map_account(debit_pdiff_account)
                if not debit_pdiff_account:
                    continue
                line_ids = move.line_ids.filtered(lambda inv_line_id: inv_line_id.exclude_from_invoice_tab and inv_line_id.is_anglo_saxon_line and inv_line_id.product_id.id == line.product_id.id and inv_line_id.product_uom_id.id == line.product_uom_id.id)
                line_ids
                if line_ids:
                    line_ids.unlink()

    def button_draft(self):
        state = self.state
        for move in self:
            move._remove_stock_account_anglo_saxon_in_lines_vals()
        rslt = super(AccountMove, self).button_draft()
        if state == 'cancel':
            for rec in self:
                if rec.purchase_order_ids:
                    for lines in rec.purchase_order_ids.mapped('order_line'):
                        line_id = rec.invoice_line_ids.filtered(lambda r: r.product_id == lines.product_id)
                        if line_id:
                            if lines.product_id.purchase_method == 'purchase':
                                if lines.qty_invoiced > lines.product_qty:
                                    raise UserError('QTY Billed > Qty PO')
                            else:
                                if lines.qty_invoiced > lines.qty_received:
                                    raise UserError('QTY Billed > Qty received')
            if rec.sale_order_ids:
                for lines in rec.sale_order_ids.mapped('order_line'):
                    line_id = rec.invoice_line_ids.filtered(lambda r: r.product_id == lines.product_id)
                    if line_id:
                        if lines.product_id.invoice_policy == 'order':
                            if lines.qty_invoiced > lines.product_uom_qty:
                                raise UserError('QTY Invoiced > Qty SO')
                        else:
                            if lines.qty_invoiced > lines.qty_delivered:
                                raise UserError('QTY Invoiced > Qty Delivered')
        return rslt

    @api.depends('move_type', 'partner_id','branch_id')
    def _compute_purchase_order(self):
        for record in self:
            purchase_order_ids = []
            if record.move_type == 'in_invoice' and record.partner_id and record.branch_id:
                purchase_order_ids = self.env['purchase.order'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('state', '=', 'purchase'),
                    ('invoice_status', '=', 'to invoice'),
                    ('is_services_orders','!=',True),
                    ('branch_id','=',record.branch_id.id)
                ])
                purchase_order_ids = purchase_order_ids.ids
            record.filter_purchase_order_ids = json.dumps([('id','in', purchase_order_ids)])
            
            # if record.move_type == 'in_invoice' and record.partner_id:
            #     self.env.cr.execute("""
            #         SELECT id
            #         FROM purchase_order
            #         WHERE partner_id = %s and state = 'purchase' and invoice_status = 'to invoice' AND is_services_orders != TRUE
            #     """ % (record.partner_id.id))
            #     purchase_order_ids = self.env.cr.fetchall()
            # record.filter_purchase_order_ids = json.dumps([('id','in', list(map(itemgetter(0), purchase_order_ids)))])
    

    @api.depends('sale_order_ids', 'purchase_order_ids', 'partner_id')
    def _compute_picking(self):
        for record in self:
            picking_ids = []
            if record.partner_id:
                if record.move_type == 'out_invoice':
                    picking_ids = record.sale_order_ids.picking_ids.ids
                    if not picking_ids:
                        pick_ids = self.env['stock.picking'].search([
                            ('state', '=', 'done'), 
                            ('partner_id', '=', record.partner_id.id),
                            ('picking_type_id.code', '=', 'outgoing'),
                            ('inv_line_ids', '=', False),
                        ])
                        for line_picking in pick_ids:
                            if not line_picking.inv_line_ids:
                                picking_ids += line_picking.ids

                elif record.move_type == "in_invoice":
                    # picking_ids = record.purchase_order_ids.picking_ids.ids
                    picking_ids = record.po_reference_ids.mapped('picking_ids').ids
                    if not picking_ids:
                        pick_ids = self.env['stock.picking'].search([
                            ('partner_id', '=', record.partner_id.id),
                            ('picking_type_id.code', '=', 'incoming'),
                            ('state', '=', 'done'),
                            ('inv_line_ids', '=', False),
                        ])
                        
                        for line_picking in pick_ids:
                            if not line_picking.inv_line_ids:
                                picking_ids += line_picking.ids
            record.filter_picking_ids = [(6, 0, picking_ids)]
            

    def action_sale_delivery(self):
        self.ensure_one()
        context = dict(self.env.context) or {}
        context.update({
            'default_move_id': self.id,
        })
        if self.picking_ids:
            data = []
            for lines in self.picking_ids.mapped('move_ids_without_package'):
                data.append((0, 0, {
                    'product_id': lines.product_id.id,
                    'quantity': lines.initial_demand,
                    'unit_price': lines.sale_line_id.price_unit,
                    'subtotal': lines.sale_line_id.price_total,
                    'picking_id': lines.picking_id.id,
                }))
            context.update({
                'default_order_picking_line_ids': data
            })
            return {
                'name': _('Delivery Order'),
                'view_mode': 'form',
                'res_model': 'order.picking',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        else:
            raise ValidationError("Delivery order quantity is 0.")

    def action_purchase_receipt(self):
        self.ensure_one()
        context = dict(self.env.context) or {}
        context.update({
            'default_move_id': self.id,
        })
        if self.picking_ids:
            data = []
            for lines in self.picking_ids.mapped('move_ids_without_package'):
                data.append((0, 0, {
                    'product_id': lines.product_id.id,
                    'quantity': lines.initial_demand,
                    'unit_price': lines.purchase_line_id.price_unit,
                    'subtotal': lines.purchase_line_id.price_total,
                    'picking_id': lines.picking_id.id,
                }))
            context.update({
                'default_order_picking_line_ids': data
            })
            return {
                'name': _('Purchase Order'),
                'view_mode': 'form',
                'res_model': 'order.picking',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        else:
            raise ValidationError("Purchase order quantity is 0.")

    @api.model
    def _move_autocomplete_invoice_lines_create(self, vals_list, create_line_discount=False):
        if not self.env.context.get('from_customer_portal', False):
            return super(AccountMove, self)._move_autocomplete_invoice_lines_create(vals_list, create_line_discount=create_line_discount)
        old_vals_list = copy.deepcopy(vals_list)
        new_vals_list = super(AccountMove, self)._move_autocomplete_invoice_lines_create(vals_list, create_line_discount=create_line_discount)
        for ovl, nvl in zip(old_vals_list, new_vals_list):
            if 'sale_order_ids' in ovl:
                nvl['sale_order_ids'] = ovl['sale_order_ids']
        return new_vals_list


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_invoice_values(self, order, name, amount, so_line):
        res = super(SaleAdvancePaymentInv,self)._prepare_invoice_values(order, name, amount, so_line)
        res['sale_order_ids'] = [(4, order.id)]
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        self.ensure_one()

        if not self.product_id:
            return 0.0

        company = self.move_id.company_id
        currency = self.move_id.currency_id
        company_currency = company.currency_id
        product_uom = self.product_id.uom_id
        fiscal_position = self.move_id.fiscal_position_id
        is_refund_document = self.move_id.move_type in ('out_refund', 'in_refund')
        move_date = self.move_id.date or fields.Date.context_today(self)

        if self.move_id.is_sale_document(include_receipts=True):
            # product_price_unit = self.product_id.lst_price
            product_price_unit = self.price_unit
            product_taxes = self.product_id.taxes_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # product_price_unit = self.product_id.standard_price
            product_price_unit = self.price_unit
            product_taxes = self.product_id.supplier_taxes_id
        else:
            return 0.0
        product_taxes = product_taxes.filtered(lambda tax: tax.company_id == company)

        # Apply unit of measure.
        if self.product_uom_id and self.product_uom_id != product_uom:
            product_price_unit = product_uom._compute_price(product_price_unit, self.product_uom_id)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes, partner=self.partner_id)

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_before_fp):
                    taxes_res = flattened_taxes_before_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                    )
                    product_price_unit = company_currency.round(taxes_res['total_excluded'])

                flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            product_price_unit += tax_res['amount']

        # Apply currency rate.
        if currency and currency != company_currency:
            product_price_unit = company_currency._convert(product_price_unit, currency, company, move_date)

        return product_price_unit