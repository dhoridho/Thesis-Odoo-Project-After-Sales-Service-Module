from odoo import models, fields, api
from datetime import datetime, timedelta, date


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_invoice = fields.Boolean(string="Project Invoice", default=False)
    penalty_invoice = fields.Boolean(string="Progressive Claim Required", default=False)
    progressive_method = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
    ], string='Progressive Method')
    project_id = fields.Many2one('project.project', string="Project")
    cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet')
    project_budget = fields.Many2one('project.budget', string='Project Budget')
    progress = fields.Float('Progress', readonly='1', digits=(2, 2))
    progressline = fields.Float('Progressline', readonly='1', digits=(2, 2))
    claim_description = fields.Char('Claim ID', default=False)
    claim_id = fields.Many2one('progressive.claim',
                               'Progressive Claim',
                               ondelete='restrict',
                               store=True)
    gross_amount = fields.Monetary(string="Gross Amount", currency_field='company_currency_id')
    dp_deduction = fields.Monetary('DP Deduction', currency_field='company_currency_id')
    retention_deduction = fields.Monetary('Retention Deduction', currency_field='company_currency_id')
    amount_deduction = fields.Monetary(string="Amount After Deduction", currency_field='currency_id')
    tax_amount = fields.Monetary(string="Tax Amount", currency_field='currency_id')
    amount_invoice = fields.Monetary(string="Amount Invoice", currency_field='currency_id')
    tax_id = fields.Many2many('account.tax', 'taxes_id', 'move_line_id', string="Taxes",
                              help="Taxes that apply on the base amount")
    contract_parent = fields.Many2one('sale.order.const', string="Parent Contract")
    contract_parent_po = fields.Many2one('purchase.order', string="Parent Contract")
    job_estimate_id = fields.Many2one('job.estimate', string="BOQ")
    amount_untaxed_2 = fields.Float(string='Untaxed Amount', currency_field='currency_id',
                                    compute='_compute_amount_const')
    milestone_id = fields.Many2one('account.milestone.term.const', string="Milestone ID")
    journal_claim_id = fields.Many2one('progressive.claim', string='Claim ID', ondelete='cascade')
    request_id = fields.Many2one('claim.request.line', string="Request ID")
    progressive_bill = fields.Boolean('Progressive Bill')
    cancelled_contract_so = fields.Many2one('sale.order.const', string="Cancelled Contract")
    cancelled_contract_po = fields.Many2one('purchase.order', string="Cancelled Contract")
    cancelled_job_estimate = fields.Many2one('job.estimate', string="Cancelled BOQ")
    total_claim = fields.Monetary(string="Total Claimed", currency_field='currency_id', compute='_set_total_claim')
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    po_subcon_line_id = fields.Many2one('rfq.variable.line', string="Purchase Order Subcon Line")
    project_task_id = fields.Many2one('project.task', string="Project Task")

    # Cost Sheet and Budget summary for procurement bills
    procurement_cost_sheet_id = fields.Many2one(related="purchase_order_id.cost_sheet")
    procurement_cost_sheet_material_ids = fields.One2many(related="procurement_cost_sheet_id.material_ids")
    procurement_cost_sheet_labour_ids = fields.One2many(related="procurement_cost_sheet_id.material_labour_ids")
    procurement_cost_sheet_overhead_ids = fields.One2many(related="procurement_cost_sheet_id.material_overhead_ids")
    procurement_cost_sheet_equipment_ids = fields.One2many(related="procurement_cost_sheet_id.material_equipment_ids")
    procurement_cost_sheet_subcon_ids = fields.One2many(related="procurement_cost_sheet_id.material_subcon_ids")
    procurement_cost_sheet_internal_asset_ids = fields.One2many(related="procurement_cost_sheet_id.internal_asset_ids")
    procurement_cost_sheet_material_gop_ids = fields.One2many(related="procurement_cost_sheet_id.material_gop_ids")
    procurement_cost_sheet_labour_gop_ids = fields.One2many(related="procurement_cost_sheet_id.material_labour_gop_ids")
    procurement_cost_sheet_overhead_gop_ids = fields.One2many(related="procurement_cost_sheet_id.material_overhead_gop_ids")
    procurement_cost_sheet_equipment_gop_ids = fields.One2many(related="procurement_cost_sheet_id.material_equipment_gop_ids")

    procurement_project_budget_id = fields.Many2one(related="purchase_order_id.project_budget")
    procurement_project_budget_material_ids = fields.One2many(related="procurement_project_budget_id.budget_material_ids")
    procurement_project_budget_labour_ids = fields.One2many(related="procurement_project_budget_id.budget_labour_ids")
    procurement_project_budget_overhead_ids = fields.One2many(related="procurement_project_budget_id.budget_overhead_ids")
    procurement_project_budget_equipment_ids = fields.One2many(related="procurement_project_budget_id.budget_equipment_ids")
    procurement_project_budget_subcon_ids = fields.One2many(related="procurement_project_budget_id.budget_subcon_ids")
    procurement_project_budget_internal_asset_ids = fields.One2many(related="procurement_project_budget_id.budget_internal_asset_ids")
    procurement_project_budget_material_gop_ids = fields.One2many(related="procurement_project_budget_id.budget_material_gop_ids")
    procurement_project_budget_labour_gop_ids = fields.One2many(related="procurement_project_budget_id.budget_labour_gop_ids")
    procurement_project_budget_overhead_gop_ids = fields.One2many(related="procurement_project_budget_id.budget_overhead_gop_ids")
    procurement_project_budget_equipment_gop_ids = fields.One2many(related="procurement_project_budget_id.budget_equipment_gop_ids")

    budgeting_method = fields.Selection(related="procurement_cost_sheet_id.budgeting_method")

    @api.onchange('tax_id')
    def set_tax_id_lines(self):
        for res in self:
            for line in res.invoice_line_ids:
                line.tax_ids = res.tax_id

    @api.depends('amount_total', 'amount_residual')
    def _set_total_claim(self):
        total = 0
        for res in self:
            total = res.amount_total - res.amount_residual
            res.total_claim = total

    @api.depends('subtotal_amount')
    def _compute_amount_const(self):
        total = 0
        for res in self:
            total = res.subtotal_amount
            res.amount_untaxed_2 = total
        return total

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for rec in self:
            if len(rec.purchase_order_ids) == 1:
                purchase = rec.purchase_order_ids
                purchase_line_type = []
                for bill in rec.invoice_line_ids:
                    if bill.purchase_line_id:
                        down_payment_amount = ((bill.purchase_line_id.price_subtotal / bill.purchase_order_id.amount_untaxed) * rec.down_payment_amount) * -1
                        down_payment_quantity = ((rec.down_payment_amount / bill.purchase_order_id.amount_untaxed) * bill.purchase_line_id.product_qty) * -1
                        bill.purchase_line_id._budget_bill_amount(bill, down_payment_amount, down_payment_quantity, -1)
                        purchase_line_type.append(bill.purchase_line_id.type)

                    if bill.name == "Down Payment":
                        if len(rec.purchase_order_ids) == 1:
                            purchase_order = rec.purchase_order_ids
                            is_gop = False
                            list_gop_table = []
                            for order_line in purchase_order.order_line:
                                down_payment_amount = (order_line.price_subtotal / purchase_order.amount_untaxed) * rec.down_payment_amount
                                down_payment_quantity = (rec.down_payment_amount / purchase_order.amount_untaxed) * order_line.product_qty
                                if order_line.type == 'material':
                                    rec._calculate_dp_reset(order_line.cs_material_id, order_line.bd_material_id,
                                                            down_payment_amount, down_payment_quantity)
                                    if order_line.cs_material_gop_id:
                                        # rec._calculate_dp_reset(order_line.cs_material_gop_id,
                                        #                         order_line.bd_material_gop_id,
                                        #                         down_payment_amount, down_payment_quantity)
                                        is_gop = True
                                        if 'material' not in list_gop_table:
                                            list_gop_table.append('material')
                                elif order_line.type == 'labour':
                                    rec._calculate_dp_reset(order_line.cs_labour_id, order_line.bd_labour_id,
                                                            down_payment_amount, down_payment_quantity)
                                    # if order_line.cs_labour_gop_id:
                                    #     rec._calculate_dp_reset(order_line.cs_labour_gop_id,
                                    #                             order_line.bd_labour_gop_id,
                                    #                             down_payment_amount, down_payment_quantity)
                                elif order_line.type == 'overhead':
                                    rec._calculate_dp_reset(order_line.cs_overhead_id, order_line.bd_overhead_id,
                                                            down_payment_amount, down_payment_quantity)
                                    if order_line.cs_overhead_gop_id:
                                        # rec._calculate_dp_reset(order_line.cs_overhead_gop_id,
                                        #                         order_line.bd_overhead_gop_id,
                                        #                         down_payment_amount, down_payment_quantity)
                                        is_gop = True
                                        if 'overhead' not in list_gop_table:
                                            list_gop_table.append('overhead')
                                elif order_line.type == 'equipment':
                                    rec._calculate_dp_reset(order_line.cs_equipment_id, order_line.bd_equipment_id,
                                                            down_payment_amount, down_payment_quantity)
                                    if order_line.cs_equipment_gop_id:
                                        # rec._calculate_dp_reset(order_line.cs_equipment_gop_id,
                                        #                         order_line.bd_equipment_gop_id,
                                        #                         down_payment_amount, down_payment_quantity)
                                        is_gop = True
                                        if 'equipment' not in list_gop_table:
                                            list_gop_table.append('equipment')
                                elif order_line.type == 'split':
                                    rec._calculate_dp_reset(order_line.cs_subcon_id, order_line.bd_subcon_id,
                                                            down_payment_amount, down_payment_quantity)
                                    # if order_line.cs_subcon_gop_id:
                                    #     rec._calculate_dp_reset(order_line.cs_subcon_gop_id,
                                    #                             order_line.bd_subcon_gop_id,
                                    #                             down_payment_amount, down_payment_quantity)

                            if is_gop:
                                if 'material' in list_gop_table:
                                    purchase_order.cost_sheet.get_gop_material_table()
                                    if purchase_order.project_budget:
                                        purchase_order.project_budget.get_gop_material_table()
                                if 'overhead' in list_gop_table:
                                    purchase_order.cost_sheet.get_gop_overhead_table()
                                    if purchase_order.project_budget:
                                        purchase_order.project_budget.get_gop_overhead_table()
                                if 'equipment' in list_gop_table:
                                    purchase_order.cost_sheet.get_gop_equipment_table()
                                    if purchase_order.project_budget:
                                        purchase_order.project_budget.get_gop_equipment_table()
                if purchase and purchase.cost_sheet.budgeting_method == 'gop_budget':
                    if 'material' in purchase_line_type:
                        purchase.cost_sheet.get_gop_material_table()
                        if purchase.project_budget:
                            purchase.project_budget.get_gop_material_table()
                    if 'overhead' in purchase_line_type:
                        purchase.cost_sheet.get_gop_overhead_table()
                        if purchase.project_budget:
                            purchase.project_budget.get_gop_overhead_table()
                    if 'equipment' in purchase_line_type:
                        purchase.cost_sheet.get_gop_equipment_table()
                        if purchase.project_budget:
                            purchase.project_budget.get_gop_equipment_table()
            if len(rec.project_task_id) > 0:
                for bill in rec.invoice_line_ids:
                    if len(bill.labour_usage_line_id) > 0:
                        for cs in bill.labour_usage_line_id.cs_labour_id:
                            cs.billed_amt -= bill.debit
                        for bd in bill.labour_usage_line_id.bd_labour_id:
                            bd.billed_amt -= bill.debit

        return res

    def action_post(self):
        res = super(AccountMove, self).action_post()
        purchase = False
        for bill_id in self:
            if len(bill_id.purchase_order_ids) == 1:
                purchase = bill_id.purchase_order_ids
            if purchase:
                purchase_line_type = []
                for bill in bill_id.invoice_line_ids:
                    if bill.purchase_line_id:
                        down_payment_percentage = bill.purchase_line_id.order_id.down_payment_amount / bill.purchase_line_id.order_id.amount_total
                        down_payment_tax = bill.purchase_line_id.order_id.down_payment_amount - (bill.purchase_line_id.order_id.amount_untaxed * down_payment_percentage)
                        total_down_payment_amount = bill.purchase_line_id.order_id.down_payment_amount - down_payment_tax

                        down_payment_amount = ((bill.purchase_line_id.price_subtotal / bill.purchase_order_id.amount_untaxed) * total_down_payment_amount)
                        down_payment_quantity = ((total_down_payment_amount / bill.purchase_order_id.amount_untaxed) * bill.purchase_line_id.product_qty)
                        bill.purchase_line_id._budget_bill_amount(bill, down_payment_amount, down_payment_quantity, 1)
                        purchase_line_type.append(bill.purchase_line_id.type)
                    if bill.is_down_payment and len(bill_id.invoice_line_ids) == 1:
                        bill_id.actualized_purchase_order_down_payment()

                if purchase and purchase.cost_sheet.budgeting_method == 'gop_budget':
                    if 'material' in purchase_line_type:
                        purchase.cost_sheet.get_gop_material_table()
                        if purchase.project_budget:
                            purchase.project_budget.get_gop_material_table()
                    if 'overhead' in purchase_line_type:
                        purchase.cost_sheet.get_gop_overhead_table()
                        if purchase.project_budget:
                            purchase.project_budget.get_gop_overhead_table()
                    if 'equipment' in purchase_line_type:
                        purchase.cost_sheet.get_gop_equipment_table()
                        if purchase.project_budget:
                            purchase.project_budget.get_gop_equipment_table()

            if len(bill_id.project_task_id) > 0:
                for bill in bill_id.invoice_line_ids:
                    if len(bill.labour_usage_line_id) > 0:
                        for cs in bill.labour_usage_line_id.cs_labour_id:
                            cs.billed_amt += bill.debit
                            # cs.billed_qty += bill.quantity
                        for bd in bill.labour_usage_line_id.bd_labour_id:
                            bd.billed_amt += bill.debit

                        # for gop_cs in bill.labour_usage_line_id.cs_labour_gop_id:
                        #     gop_cs.billed_amt += bill.debit

            bill_id.actualized_bill_subcon()
        return res

    def _calculate_dp_actualization(self, cost_sheet_field, budget_field, down_payment_amount, down_payment_quantity):
        if budget_field:
            cost_sheet_field.write({
                'billed_amt': cost_sheet_field.billed_amt + down_payment_amount,
                'billed_qty': cost_sheet_field.billed_qty + down_payment_quantity,
            })
            budget_field.write({
                'billed_amt': budget_field.billed_amt + down_payment_amount,
                'billed_qty': budget_field.billed_qty + down_payment_quantity,
            })
        else:
            cost_sheet_field.write({
                'billed_amt': budget_field.billed_amt + down_payment_amount,
                'billed_qty': budget_field.billed_qty + down_payment_quantity,
            })

    def _calculate_dp_reset(self, cost_sheet_field, budget_field, down_payment_amount, down_payment_quantity):
        if budget_field:
            cost_sheet_field.write({
                'billed_amt': cost_sheet_field.billed_amt - down_payment_amount,
                'billed_qty': cost_sheet_field.billed_qty - down_payment_quantity,
            })
            budget_field.write({
                'billed_amt': budget_field.billed_amt - down_payment_amount,
                'billed_qty': budget_field.billed_qty - down_payment_quantity,
            })
        else:
            cost_sheet_field.write({
                'billed_amt': budget_field.billed_amt - down_payment_amount,
                'billed_qty': budget_field.billed_qty - down_payment_quantity,
            })

    def actualized_purchase_order_down_payment(self):
        for rec in self:
            if len(rec.purchase_order_ids) == 1:
                purchase_order = rec.purchase_order_ids
                is_gop = False
                list_gop_table = []
                for order_line in purchase_order.order_line:
                    down_payment_amount = (order_line.price_subtotal / purchase_order.amount_total) * rec.down_payment_amount
                    down_payment_quantity = (rec.down_payment_amount / purchase_order.amount_total) * order_line.product_qty
                    if order_line.type == 'material':
                        rec._calculate_dp_actualization(order_line.cs_material_id, order_line.bd_material_id,
                                                        down_payment_amount, down_payment_quantity)
                        if order_line.cs_material_gop_id:
                            # rec._calculate_dp_actualization(order_line.cs_material_gop_id,
                            #                                 order_line.bd_material_gop_id,
                            #                                 down_payment_amount, down_payment_quantity)
                            is_gop = True
                            if 'material' not in list_gop_table:
                                list_gop_table.append('material')
                    elif order_line.type == 'labour':
                        rec._calculate_dp_actualization(order_line.cs_labour_id, order_line.bd_labour_id,
                                                        down_payment_amount, down_payment_quantity)
                        # if order_line.cs_labour_gop_id:
                        #     rec._calculate_dp_actualization(order_line.cs_labour_gop_id, order_line.bd_labour_gop_id,
                        #                                     down_payment_amount, down_payment_quantity)
                    elif order_line.type == 'overhead':
                        rec._calculate_dp_actualization(order_line.cs_overhead_id, order_line.bd_overhead_id,
                                                        down_payment_amount, down_payment_quantity)
                        if order_line.cs_overhead_gop_id:
                            # rec._calculate_dp_actualization(order_line.cs_overhead_gop_id,
                            #                                 order_line.bd_overhead_gop_id,
                            #                                 down_payment_amount, down_payment_quantity)
                            # Just refresh the values since its from its product after all
                            is_gop = True
                            if 'overhead' not in list_gop_table:
                                list_gop_table.append('overhead')
                    elif order_line.type == 'equipment':
                        rec._calculate_dp_actualization(order_line.cs_equipment_id, order_line.bd_equipment_id,
                                                        down_payment_amount, down_payment_quantity)
                        if order_line.cs_equipment_gop_id:
                            # rec._calculate_dp_actualization(order_line.cs_equipment_gop_id,
                            #                                 order_line.bd_equipment_gop_id,
                            #                                 down_payment_amount, down_payment_quantity)
                            # Just refresh the values since its from its product after all
                            is_gop = True
                            if 'equipment' not in list_gop_table:
                                list_gop_table.append('equipment')
                    elif order_line.type == 'split':
                        rec._calculate_dp_actualization(order_line.cs_subcon_id, order_line.bd_subcon_id,
                                                        down_payment_amount, down_payment_quantity)
                        # if order_line.cs_split_gop_id:
                        #     rec._calculate_dp_actualization(order_line.cs_subcon_gop_id,
                        #                                     order_line.bd_subcon_gop_id,
                        #                                     down_payment_amount, down_payment_quantity)

                if is_gop:
                    if 'material' in list_gop_table:
                        purchase_order.cost_sheet.get_gop_material_table()
                        if purchase_order.project_budget:
                            purchase_order.project_budget.get_gop_material_table()
                    if 'overhead' in list_gop_table:
                        purchase_order.cost_sheet.get_gop_overhead_table()
                        if purchase_order.project_budget:
                            purchase_order.project_budget.get_gop_overhead_table()
                    if 'equipment' in list_gop_table:
                        purchase_order.cost_sheet.get_gop_equipment_table()
                        if purchase_order.project_budget:
                            purchase_order.project_budget.get_gop_equipment_table()

    def actualized_bill_subcon(self):
        for rec in self:
            if rec.claim_id.progressive_bill:
                if rec.claim_id.contract_parent_po:
                    claim_history = rec.env['project.claim'].search([('invoice_id', '=', rec.id)])
                    for subcon in rec.claim_id.contract_parent_po.variable_line_ids:
                        if 'Down Payment' in rec.claim_description:
                            amount = claim_history.amount_untaxed * subcon.dp_amount_percentage
                            quantity = (amount / subcon.total) * subcon.quantity

                            rec.update_subcon(subcon, amount, quantity)
                        elif 'Progressive' in rec.claim_description:
                            if rec.po_subcon_line_id.id == subcon.id:
                                amount = claim_history.amount_untaxed
                                quantity = (amount / subcon.total) * subcon.quantity

                                rec.update_subcon(subcon, amount, quantity)
                        elif 'Retention 1' in rec.claim_description:
                            amount = claim_history.amount_untaxed * subcon.dp_amount_percentage
                            quantity = (amount / subcon.total) * subcon.quantity

                            rec.update_subcon(subcon, amount, quantity)
                        elif 'Retention 2' in rec.claim_description:
                            amount = claim_history.amount_untaxed * subcon.dp_amount_percentage
                            quantity = (amount / subcon.total) * subcon.quantity

                            rec.update_subcon(subcon, amount, quantity)

    def update_subcon(self, subcon, amount, quantity):
        subcon.cs_subcon_id.write({
            'billed_amt': subcon.cs_subcon_id.billed_amt + amount,
            'billed_qty': subcon.cs_subcon_id.billed_qty + quantity,
        })
        subcon.bd_subcon_id.write({
            'billed_amt': subcon.bd_subcon_id.billed_amt + amount,
            'billed_qty': subcon.bd_subcon_id.billed_qty + quantity,
        })

    def unlink(self):
        claim_id = []
        for res in self:
            project_journal_entry = self.env['project.journal.entry'].search([('request_id', '=', res.request_id.id)])
            if project_journal_entry:
                project_journal_entry.unlink()
            if res.claim_id.id not in claim_id:
                claim_id.append(res.claim_id.id)
        r = super(AccountMove, self).unlink()
        for id in claim_id:
            claim = self.env['progressive.claim'].search([('id', '=', id)])
            claim.sudo()._compute_count_invoices()
            claim.sudo()._compute_taxes_amount()
            for line in claim.taxes_ids:
                if line.amount_tax == 0:
                    line.unlink()
        return r

    @api.depends('branch_id', 'project_id')
    def _depends_analytic_group_ids(self):
        for rec in self:
            if rec.project_id:
                rec.analytic_group_ids = rec.project_id.analytic_idz
            else:
                rec.analytic_group_ids = rec.branch_id.analytic_tag_ids


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    project_invoice = fields.Boolean(related='move_id.project_invoice', string="Project Invoice")
    progress = fields.Float('Progress (%)', digits=(2, 2))
    gross_amount = fields.Monetary(string="Gross Amount", currency_field='company_currency_id')
    dp_deduction = fields.Monetary('DP Deduction', currency_field='company_currency_id')
    retention_deduction = fields.Monetary('Retention Deduction', currency_field='company_currency_id')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    price_tax = fields.Monetary(string='Tax Amount', compute='_get_price_tax', currency_field='currency_id')
    penalty_invoice = fields.Boolean(related='move_id.penalty_invoice', string="Progressive Claim Required")
    labour_usage_line_id = fields.Many2one('task.labour.usage', string="Labour Usage Line")
    remaining_budget_amount = fields.Float(related="purchase_line_id.remining_budget_amount", string="Remaining Budget")

    @api.depends('price_unit', 'tax_ids')
    def _get_price_tax(self):
        for res in self:
            total = 0.0
            for rec in res.tax_ids:
                total += rec.amount
            res.price_tax = res.price_subtotal * (total / 100)
            return total
