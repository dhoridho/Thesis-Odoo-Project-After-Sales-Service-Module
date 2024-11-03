from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    project_id = fields.Many2one('project.project', string="Project", compute='_compute_project_id')

    @api.depends('company_id')
    def _compute_project_id(self):
        context = dict(self.env.context) or {}
        account_invoice_id = self.env['account.move'].browse(context.get('active_ids'))
        if account_invoice_id.project_id:
            self.project_id = account_invoice_id.project_id.id
        else:
            self.project_id = False

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_batch(batch_result)
        payment_vals['project_id'] = self.project_id.id

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        account_invoice_id = self.env['account.move'].browse(self.env.context.get('active_id'))
        purchase = False
        if len(account_invoice_id.purchase_order_ids) == 1:
            purchase = account_invoice_id.purchase_order_ids
            purchase_line_type = []
            for line in account_invoice_id.invoice_line_ids:
                if line.is_down_payment and len(account_invoice_id.invoice_line_ids) == 1:
                    # Payment Down Payment actualization
                    # Has seperate method from PO payment because DP has difference cases
                    self.actualized_purchase_order_down_payment(account_invoice_id)

                if line.purchase_line_id and not line.is_down_payment:
                    total_tax_amount = 0
                    untaxed_down_payment_amount = 0
                    # getting untaxed amount of each line's DP
                    if (account_invoice_id.amount_total + (account_invoice_id.down_payment_amount * -1)) != 0:
                        line_percentage = line.purchase_line_id.price_subtotal / line.purchase_line_id.order_id.amount_untaxed

                        down_payment_percentage = (account_invoice_id.down_payment_amount / (account_invoice_id.amount_total + (account_invoice_id.down_payment_amount * -1))) * -1
                        down_payment_amount = (account_invoice_id.down_payment_amount * line_percentage) * -1
                        down_payment_tax = (down_payment_amount - (line.purchase_line_id.price_subtotal * down_payment_percentage))

                        untaxed_down_payment_amount = down_payment_amount - down_payment_tax

                    # Tax calculation for PO payment
                    if len(account_invoice_id.amount_by_group) > 0:
                        total_tax_amount += (account_invoice_id.amount_by_group[0][1] *
                                             (self.amount / (account_invoice_id.amount_total)))
                        amount = (self.amount - total_tax_amount)
                    else:
                        amount = self.amount

                    # Purchase Order Actualization

                    line.purchase_line_id._budget_purchased_amount(amount, untaxed_down_payment_amount)
                    purchase_line_type.append(line.purchase_line_id.type)

                    # Left over budgeted amount from Purchase Order actualization
                    budget_amount = line.purchase_line_id.budget_unit_price * line.purchase_line_id.product_qty
                    purchase_amount = line.purchase_line_id.price_unit * line.purchase_line_id.product_qty

                    if purchase_amount < budget_amount:
                        if ((account_invoice_id.amount_residual == 0 and not line.is_down_payment) or
                                (self.payment_difference_handling == 'reconcile' and len(self.difference_ids) > 0)):

                            percentage = line.purchase_line_id.price_subtotal / line.purchase_line_id.order_id.amount_untaxed
                            if self.payment_difference_handling == 'reconcile':
                                payment_difference_tax_amount = percentage * (
                                            account_invoice_id.amount_by_group[0][1] * (self.payment_difference / (account_invoice_id.amount_total)))
                                payment_difference = (self.payment_difference - payment_difference_tax_amount)
                                reconcile_amount = payment_difference
                                reconcile_quantity = ((payment_difference / line.purchase_line_id.order_id.amount_untaxed) * line.purchase_line_id.product_qty)

                                self.create_budget_left_amount(line.purchase_line_id, purchase_amount, budget_amount,
                                                               reconcile_amount,
                                                               reconcile_quantity)
                            else:
                                self.create_budget_left_amount(line.purchase_line_id, purchase_amount, budget_amount, )

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
        if len(account_invoice_id.project_task_id) > 0:
            for bill in account_invoice_id.invoice_line_ids:
                if len(bill.labour_usage_line_id) > 0:
                    for cs in bill.labour_usage_line_id.cs_labour_id:
                        cs.billed_amt -= self.amount
                        cs.purchased_amt += self.amount
                        # cs.billed_qty += bill.quantity
                    for bd in bill.labour_usage_line_id.bd_labour_id:
                        bd.billed_amt -= self.amount
                        bd.purchased_amt += self.amount
        self.actualized_paid_subcon(account_invoice_id)

        return res

    def _calculate_dp_actualization(self, estimated_dp_budget_amount, cost_sheet_field, budget_field, down_payment_amount, down_payment_quantity):
        reserved_return_amount = (estimated_dp_budget_amount - down_payment_amount) if estimated_dp_budget_amount > down_payment_amount else 0
        reserved_over_amount = (estimated_dp_budget_amount - down_payment_amount) if estimated_dp_budget_amount < down_payment_amount else 0
        if budget_field:
            cost_sheet_field.write({
                'reserved_amt': cost_sheet_field.reserved_amt - down_payment_amount,
                'reserved_qty': cost_sheet_field.reserved_qty - down_payment_quantity,
                'billed_amt': cost_sheet_field.billed_amt - down_payment_amount,
                'billed_qty': cost_sheet_field.billed_qty - down_payment_quantity,
                'purchased_amt': cost_sheet_field.purchased_amt + down_payment_amount,
                'purchased_qty': cost_sheet_field.purchased_qty + down_payment_quantity,
                'po_reserved_qty': cost_sheet_field.po_reserved_qty - down_payment_quantity,
                'reserved_return_amount': cost_sheet_field.reserved_return_amount - reserved_return_amount,
                'reserved_over_amount': cost_sheet_field.reserved_over_amount - abs(reserved_over_amount),
                'amount_return': cost_sheet_field.amount_return + reserved_return_amount,
                'over_amount': cost_sheet_field.over_amount + abs(reserved_over_amount),
            })
            budget_field.write({
                'amt_res': budget_field.amt_res - down_payment_amount,
                'qty_res': budget_field.qty_res - down_payment_quantity,
                'billed_amt': budget_field.billed_amt - down_payment_amount,
                'billed_qty': budget_field.billed_qty - down_payment_quantity,
                'purchased_amt': budget_field.purchased_amt + down_payment_amount,
                'purchased_qty': budget_field.purchased_qty + down_payment_quantity,
            })
        else:
            cost_sheet_field.write({
                'reserved_amt': cost_sheet_field.reserved_amt - down_payment_amount,
                'reserved_qty': cost_sheet_field.reserved_qty - down_payment_quantity,
                'billed_amt': cost_sheet_field.billed_amt - down_payment_amount,
                'billed_qty': cost_sheet_field.billed_qty - down_payment_quantity,
                'purchased_amt': cost_sheet_field.purchased_amt + down_payment_amount,
                'purchased_qty': cost_sheet_field.purchased_qty + down_payment_quantity,
                'po_reserved_qty': cost_sheet_field.po_reserved_qty - down_payment_quantity,
                'reserved_return_amount': cost_sheet_field.reserved_return_amount - reserved_return_amount,
                'reserved_over_amount': cost_sheet_field.reserved_over_amount - abs(reserved_over_amount),
                'amount_return': cost_sheet_field.amount_return + reserved_return_amount,
                'over_amount': cost_sheet_field.over_amount + abs(reserved_over_amount),
            })

    def actualized_purchase_order_down_payment(self, invoice_id):
        for rec in self:
            if invoice_id:
                if len(invoice_id.purchase_order_ids) == 1:
                    purchase_order = invoice_id.purchase_order_ids
                    list_gop_table = []
                    for order_line in purchase_order.order_line:
                        # Getting untaxed amount of DP if taxed
                        down_payment_percentage = order_line.order_id.down_payment_amount / order_line.order_id.amount_total
                        down_payment_tax = order_line.order_id.down_payment_amount - (order_line.order_id.amount_untaxed * down_payment_percentage)
                        total_down_payment_amount = order_line.order_id.down_payment_amount - down_payment_tax

                        # Calculate value each order line
                        total_tax_amount = (down_payment_percentage * order_line.order_id.amount_tax)

                        down_payment_amount = ((order_line.price_subtotal / purchase_order.amount_untaxed)
                                               * total_down_payment_amount)
                        down_payment_quantity = ((total_down_payment_amount / purchase_order.amount_untaxed)
                                                 * order_line.product_qty)

                        # Getting actualization value for each order line for both partial and full payment
                        partial_percentage = ((rec.amount-((rec.amount/invoice_id.down_payment_amount) * total_tax_amount))
                                              / total_down_payment_amount)
                        partial_dp_amount = partial_percentage * down_payment_amount
                        partial_dp_qty = partial_percentage * down_payment_quantity
                        estimated_dp_budget_amount = ((order_line.budget_unit_price * order_line.budget_quantity) * down_payment_percentage) * partial_percentage

                        # If partial payment mark as paid, left over budgeted amount from Purchase Order
                        # will actualize to return amount
                        if (rec.amount < invoice_id.down_payment_amount and
                                rec.payment_difference_handling == 'reconcile' and len(self.difference_ids) > 0):

                            reconcile_amount = rec.payment_difference - ((rec.payment_difference / invoice_id.down_payment_amount) * total_tax_amount)
                            reconcile_quantity = (reconcile_amount/down_payment_amount) * down_payment_quantity

                            rec.create_budget_left_amount(order_line, down_payment_amount, down_payment_amount,
                                                          reconcile_amount, reconcile_quantity)

                        if order_line.type == 'material':
                            rec._calculate_dp_actualization(estimated_dp_budget_amount, order_line.cs_material_id, order_line.bd_material_id,
                                                            partial_dp_amount, partial_dp_qty)
                            if 'material' not in list_gop_table:
                                list_gop_table.append('material')
                        elif order_line.type == 'labour':
                            rec._calculate_dp_actualization(estimated_dp_budget_amount, order_line.cs_labour_id, order_line.bd_labour_id,
                                                            partial_dp_amount, partial_dp_qty)
                        elif order_line.type == 'overhead':
                            rec._calculate_dp_actualization(estimated_dp_budget_amount, order_line.cs_overhead_id, order_line.bd_overhead_id,
                                                            partial_dp_amount, partial_dp_qty)
                            if 'overhead' not in list_gop_table:
                                list_gop_table.append('overhead')
                        elif order_line.type == 'equipment':
                            rec._calculate_dp_actualization(estimated_dp_budget_amount, order_line.cs_equipment_id, order_line.bd_equipment_id,
                                                            partial_dp_amount, partial_dp_qty)
                            if 'equipment' not in list_gop_table:
                                list_gop_table.append('equipment')
                        elif order_line.type == 'split':
                            rec._calculate_dp_actualization(estimated_dp_budget_amount, order_line.cs_subcon_id, order_line.bd_subcon_id,
                                                            partial_dp_amount, partial_dp_qty)
                            # if order_line.cs_split_gop_id:
                            #     rec._calculate_dp_actualization(order_line.cs_subcon_gop_id,
                            #                                     order_line.bd_subcon_gop_id,
                            #                                     partial_dp_amount, down_payment_quantity)

                    if purchase_order.cost_sheet.budgeting_method == 'gop_budget':
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

    def actualized_paid_subcon(self, account_invoice_id):
        for rec in self:
            claim_id = account_invoice_id.claim_id
            if claim_id.progressive_bill:
                if claim_id.contract_parent_po:
                    for subcon in claim_id.contract_parent_po.variable_line_ids:
                        total_tax_amount = 0
                        if len(account_invoice_id.amount_by_group) > 0:
                            total_tax_amount += (account_invoice_id.amount_by_group[0][1]
                                                 * (rec.amount / account_invoice_id.amount_total))

                        if 'Down Payment' in account_invoice_id.claim_description:
                            amount = (rec.amount - total_tax_amount) * subcon.dp_amount_percentage
                            quantity = (amount / subcon.total) * subcon.quantity

                            rec.update_subcon(subcon, amount, quantity)
                        elif 'Progressive' in account_invoice_id.claim_description:
                            if account_invoice_id.po_subcon_line_id.id == subcon.id:
                                amount = (rec.amount - total_tax_amount)
                                quantity = (amount / subcon.total) * subcon.quantity

                                rec.update_subcon(subcon, amount, quantity)
                        elif 'Retention 1' in account_invoice_id.claim_description:
                            amount = (rec.amount - total_tax_amount) * subcon.dp_amount_percentage
                            quantity = (amount / subcon.total) * subcon.quantity

                            rec.update_subcon(subcon, amount, quantity)
                        elif 'Retention 2' in account_invoice_id.claim_description:
                            amount = (rec.amount - total_tax_amount) * subcon.dp_amount_percentage
                            quantity = (amount / subcon.total) * subcon.quantity

                            rec.update_subcon(subcon, amount, quantity)

    def update_subcon(self, subcon, amount, quantity):
        subcon.cs_subcon_id.write({
            'reserved_amt': subcon.cs_subcon_id.reserved_amt - amount,
            'reserved_qty': subcon.cs_subcon_id.reserved_qty - quantity,
            'billed_amt': subcon.cs_subcon_id.billed_amt - amount,
            'billed_qty': subcon.cs_subcon_id.billed_qty - quantity,
            'purchased_amt': subcon.cs_subcon_id.purchased_amt + amount,
            'purchased_qty': subcon.cs_subcon_id.purchased_qty + quantity,
            'actual_used_amt': subcon.cs_subcon_id.purchased_amt + amount,
            'actual_used_qty': subcon.cs_subcon_id.purchased_qty + quantity,
        })
        subcon.bd_subcon_id.write({
            'amt_res': subcon.bd_subcon_id.amt_res - amount,
            'qty_res': subcon.bd_subcon_id.qty_res - quantity,
            'billed_amt': subcon.bd_subcon_id.billed_amt - amount,
            'billed_qty': subcon.bd_subcon_id.billed_qty - quantity,
            'purchased_amt': subcon.bd_subcon_id.purchased_amt + amount,
            'purchased_qty': subcon.bd_subcon_id.purchased_qty + quantity,
            'amt_used': subcon.bd_subcon_id.purchased_amt + amount,
            'qty_used': subcon.bd_subcon_id.purchased_qty + quantity,
        })

    def update_amount_return(self, cost_sheet_line, budget_line, amount_return, reconcile_amount=0.0,
                             reconcile_quantity=0.0):
        for rec in self:
            cost_sheet_line.write({
                'reserved_amt': cost_sheet_line.reserved_amt - reconcile_amount,
                'reserved_qty': cost_sheet_line.reserved_qty - reconcile_quantity,
                'billed_amt': cost_sheet_line.billed_amt - reconcile_amount,
                'billed_qty': cost_sheet_line.billed_qty - reconcile_quantity,
                'purchased_qty': cost_sheet_line.purchased_qty + reconcile_quantity,
                'amount_return': cost_sheet_line.amount_return + amount_return,
            })
            if budget_line:
                budget_line.write({
                    'amt_res': budget_line.amt_res - reconcile_amount,
                    'qty_res': budget_line.qty_res - reconcile_quantity,
                    'billed_amt': budget_line.billed_amt - reconcile_amount,
                    'billed_qty': budget_line.billed_qty - reconcile_quantity,
                    'purchased_qty': budget_line.purchased_qty + reconcile_quantity,
                    'amount_return': budget_line.amount_return + amount_return,
                })

    def update_claim_budget_left_history(self, purchase_line, cost_claim_left_history_field,
                                         budget_claim_left_history_field,
                                         cost_sheet_line, budget_line, amount_return, budget_amount, product_type):
        for rec in self:
            cost_sheet = cost_sheet_line.job_sheet_id
            purchase_order = purchase_line.order_id.id
            if cost_sheet:
                if product_type != 'subcon':
                    cost_claim_left_history_field.create({
                        'purchase_order_id': purchase_order,
                        'job_sheet_id': cost_sheet.id,
                        'type': product_type,
                        'project_scope_id': cost_sheet_line.project_scope.id,
                        'section_id': cost_sheet_line.section_name.id,
                        'group_of_product_id': cost_sheet_line.group_of_product.id,
                        'product_id': cost_sheet_line.product_id.id,
                        'subcon_id': False,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budget_amount': budget_amount,
                        'budget_claim_amount': amount_return,
                    })
                else:
                    cost_claim_left_history_field.create({
                        'purchase_order_id': purchase_order,
                        'job_sheet_id': cost_sheet.id,
                        'type': product_type,
                        'project_scope_id': cost_sheet_line.project_scope.id,
                        'section_id': cost_sheet_line.section_name.id,
                        'group_of_product_id': False,
                        'product_id': False,
                        'subcon_id': cost_sheet_line.subcon_id.id,
                        'uom_id': cost_sheet_line.uom_id.id,
                        'budget_amount': cost_sheet_line.subcon_amount_total,
                        'budget_claim_amount': amount_return,
                    })

                cost_sheet.write({
                    'amount_from_budget': cost_sheet.amount_from_budget + amount_return,
                })
                if budget_line:
                    project_budget = budget_line.budget_id
                    if project_budget:
                        if product_type != 'subcon':
                            budget_claim_left_history_field.create({
                                'purchase_order_id': purchase_order,
                                'project_budget_id': project_budget.id,
                                'type': product_type,
                                'project_scope_id': budget_line.project_scope.id,
                                'section_id': budget_line.section_name.id,
                                'group_of_product_id': budget_line.group_of_product.id,
                                'product_id': budget_line.product_id.id,
                                'subcon_id': False,
                                'uom_id': budget_line.uom_id.id,
                                'budget_amount': budget_amount,
                                'budget_claim_amount': amount_return,
                            })
                        else:
                            budget_claim_left_history_field.create({
                                'purchase_order_id': purchase_order,
                                'project_budget_id': project_budget.id,
                                'type': product_type,
                                'project_scope_id': budget_line.project_scope.id,
                                'section_id': budget_line.section_name.id,
                                'group_of_product_id': False,
                                'product_id': False,
                                'subcon_id': budget_line.subcon_id.id,
                                'uom_id': budget_line.uom_id.id,
                                'budget_amount': budget_amount,
                                'budget_claim_amount': amount_return,
                            })

    def create_budget_left_amount(self, purchase_line, amount, budget_amount, reconcile_amount=0.0,
                                  reconcile_quantity=0.0):
        for rec in self:
            amount_return = 0
            if amount < budget_amount:
                amount_return += (budget_amount - amount)
            if reconcile_amount > 0 and reconcile_quantity > 0:
                amount_return += reconcile_amount
            if purchase_line.type == 'material':
                rec.update_amount_return(purchase_line.cs_material_id, purchase_line.bd_material_id, amount_return,
                                         reconcile_amount, reconcile_quantity)
                rec.update_claim_budget_left_history(
                    purchase_line, purchase_line.cs_material_id.job_sheet_id.material_budget_claim_history_cost_ids,
                    purchase_line.bd_material_id.budget_id.material_budget_claim_history_ids,
                    purchase_line.cs_material_id, purchase_line.bd_material_id, amount_return, budget_amount,
                    'material')
            elif purchase_line.type == 'labour':
                rec.update_amount_return(purchase_line.cs_labour_id, purchase_line.bd_labour_id, amount_return,
                                         reconcile_amount, reconcile_quantity)
                rec.update_claim_budget_left_history(
                    purchase_line, purchase_line.cs_labour_id.job_sheet_id.labour_budget_claim_history_cost_ids,
                    purchase_line.bd_labour_id.budget_id.labour_budget_claim_history_ids,
                    purchase_line.cs_labour_id, purchase_line.bd_labour_id, amount_return, budget_amount, 'labour')
            elif purchase_line.type == 'overhead':
                rec.update_amount_return(purchase_line.cs_overhead_id, purchase_line.bd_overhead_id, amount_return,
                                         reconcile_amount, reconcile_quantity)
                rec.update_claim_budget_left_history(
                    purchase_line, purchase_line.cs_overhead_id.job_sheet_id.overhead_budget_claim_history_cost_ids,
                    purchase_line.bd_overhead_id.budget_id.overhead_budget_claim_history_ids,
                    purchase_line.cs_overhead_id, purchase_line.bd_overhead_id, amount_return, budget_amount,
                    'overhead')
            elif purchase_line.type == 'equipment':
                rec.update_amount_return(purchase_line.cs_equipment_id, purchase_line.bd_equipment_id, amount_return,
                                         reconcile_amount, reconcile_quantity)
                rec.update_claim_budget_left_history(
                    purchase_line, purchase_line.cs_equipment_id.job_sheet_id.equipment_budget_claim_history_cost_ids,
                    purchase_line.bd_equipment_id.budget_id.equipment_budget_claim_history_ids,
                    purchase_line.cs_equipment_id, purchase_line.bd_equipment_id, amount_return, budget_amount,
                    'equipment')
            elif purchase_line.type == 'split':
                rec.update_amount_return(purchase_line.cs_subcon_id, purchase_line.bd_subcon_id, amount_return,
                                         reconcile_amount, reconcile_quantity)
                rec.update_claim_budget_left_history(
                    purchase_line, purchase_line.cs_subcon_id.job_sheet_id.subcon_budget_claim_history_cost_ids,
                    purchase_line.bd_subcon_id.budget_id.subcon_budget_claim_history_ids,
                    purchase_line.cs_subcon_id, purchase_line.bd_subcon_id, amount_return, budget_amount, 'subcon')
