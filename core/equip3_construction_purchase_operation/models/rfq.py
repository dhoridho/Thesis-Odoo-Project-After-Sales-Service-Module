from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools.misc import formatLang, get_lang
import odoo.addons.decimal_precision as dp


class RequestForQuotations(models.Model):
    _inherit = 'purchase.order'

    penalty_id = fields.Many2one('construction.penalty', string="Penalty")
    diff_penalty = fields.Boolean(string='Different Penalty')
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage')
    amount = fields.Float(string='Amount')
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                                     default='percentage')
    amount_client = fields.Float(string='Amount')
    note = fields.Html(string='Description', readonly=True,
                       states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
                               'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)],
                               'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})

    project = fields.Many2one('project.project', 'Project', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    cost_sheet = fields.Many2one('job.cost.sheet', string="Cost Sheet")
    project_budget = fields.Many2one('project.budget', string='Periodical Budget', domain="[('project_id','=',project), ('state','=','in_progress')]")
    multiple_budget_ids = fields.Many2many('project.budget', string='Multiple Budget', domain="[('project_id','=',project), ('state','=','in_progress')]")
    is_multiple_budget = fields.Boolean('Multiple Budget', default=False)
    down_payment_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], string="Down Payment Method",
                                           default='per')
    down_payment = fields.Float('Down Payment')
    dp_amount = fields.Float('Down Payment', compute='_compute_total_downpayment')
    variable_discount_type = fields.Selection([('global', 'Global'), ('line', 'Line')], string="Discount Applies to",
                                              default='global')
    retention_1 = fields.Float('Retention 1 (%)')
    retention_1_date = fields.Date('Retention 1 Date')
    retention_2 = fields.Float('Retention 2 (%)')
    retention_2_date = fields.Date('Retention 2 Date')
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=[('active', '=', True), ('type_tax_use', '=', 'purchase')])
    sub_contracting = fields.Selection([('main_contract', 'Main Contract'), ('addendum', 'Addendum')],
                                       string="Contract Category", readonly=True,
                                       states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
                                               'waiting_for_approval': [('readonly', False)],
                                               'to approve': [('readonly', False)],
                                               'rfq_approved': [('readonly', False)],
                                               'request_for_amendment': [('readonly', False)]})
    split_material = fields.Boolean('Split Material', default=False)
    subcon_contract = fields.Many2one('purchase.order', string='Subcon Purchase Order',
                                      domain="[('project','=', project), ('is_subcontracting', '=', True)]")
    split_po = fields.Many2many('purchase.order', relation="related_purchase_rel_id", column1="purchase_id",
                                column2="contract_id", string='Material Purchase Order',
                                domain="[('project','=', project), ('is_material_orders', '=', True)]")
    is_subcontracting = fields.Boolean('Is Subcontracting', default=False)
    is_material_orders = fields.Boolean('Is Material Orders', default=False)
    is_orders = fields.Boolean('Is Orders', default=False)
    is_asset_cons_order = fields.Boolean('Is Asset Cons Order', default=False)
    is_continue_over_budget = fields.Boolean('Is Continue', default=False)

    main_po_reference = fields.Many2one('purchase.order', 'Main PO Reference')
    addendum_payment_method = fields.Selection([('join_payment', 'Join Payment'), ('split_payment', 'Split Payment')],
                                               string="Addendum Payment Method", default=False)
    contract_parent_po = fields.Many2one('purchase.order', string="Parent Contract")
    discount_method_global = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], string="Method")
    discount_amount_global = fields.Float(string="Amount")
    related_contract_ids = fields.Many2many("purchase.order",
                                            relation="related_purchase_rel_id",
                                            column1="purchase_id",
                                            column2="contract_id",
                                            string="")
    use_retention = fields.Boolean(string="Use Retention", default=True)
    use_dp = fields.Boolean(string="Use Down Payment", default=True)
    gop_budget_ids = fields.One2many('rfq.budget.gop.line', 'purchase_id', string='Group of Product Budget')
    count_contract = fields.Integer(compute="_compute_count_contract")
    start_date = fields.Date("Planned Start Date", default=fields.Date.context_today, help="Enter start date",
                             readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
                                                    'waiting_for_approval': [('readonly', False)],
                                                    'to approve': [('readonly', False)],
                                                    'rfq_approved': [('readonly', False)],
                                                    'request_for_amendment': [('readonly', False)]})
    duration = fields.Integer("Duration", help="Duration in months", readonly=True, force_save=True)
    end_date = fields.Date("Planned End Date", help="Enter end date", readonly=True,
                           states={'draft': [('readonly', False)], 'sent': [('readonly', False)],
                                   'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)],
                                   'rfq_approved': [('readonly', False)],
                                   'request_for_amendment': [('readonly', False)]})

    contract_customer = fields.Many2one('sale.order.const', string='Customer Contract')
    retention_term_1 = fields.Many2one(
        'retention.term', string='Retention 1 Term', check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    retention_term_2 = fields.Many2one(
        'retention.term', string='Retention 2 Term', check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')
    
    is_multiple_budget_procurement = fields.Boolean(string="Is Multiple Budget", compute='_is_multiple_budget_procurement')
    count_subcon = fields.Integer(compute='_compute_count_subcon')
    report_street = fields.Char(string="Street", compute='get_report_street')
    report_country = fields.Char(string="Country", compute='get_report_country')
    report_taxes = fields.Char(string="Taxes", compute='_compute_report_tax')
    report_title = fields.Char(string="Report Title", compute='get_report_title')

    def _compute_count_subcon(self):
        for rec in self:
            total_count = 0
            if rec.variable_line_ids:
                total_count = rec.env['project.task'].search_count([('purchase_subcon', '=', rec.id)])
            rec.count_subcon = total_count

    def _is_multiple_budget_procurement(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_multiple_budget_procurement = IrConfigParam.get_param('is_multiple_budget_procurement')
        for record in self:
            record.is_multiple_budget_procurement = is_multiple_budget_procurement

    def get_report_street(self):
        for rec in self:
            if rec.project.sale_order_main.partner_id.street and rec.project.sale_order_main.partner_id.city and rec.project.sale_order_main.partner_id.state_id.name and rec.project.sale_order_main.partner_id.country_id.name:
                address_street = rec.project.sale_order_main.partner_id.street + ", " + rec.project.sale_order_main.partner_id.city + ", "
                rec.report_street = address_street
            else:
                rec.report_street = ""

    def get_report_country(self):
        for rec in self:
            if rec.project.sale_order_main.partner_id.street and rec.project.sale_order_main.partner_id.city and rec.project.sale_order_main.partner_id.state_id.name and rec.project.sale_order_main.partner_id.country_id.name:
                address_country = rec.project.sale_order_main.partner_id.state_id.name + ", " + str(rec.project.sale_order_main.partner_id.country_id.name)
                rec.report_country = address_country
            else:
                rec.report_country = ""

    def get_report_title(self):
        for rec in self:
            if rec.state == 'purchase':
                rec.report_title = "Purchase Order" + " - " + rec.name
            else:
                rec.report_title = "Request For Quotation" + " - " + rec.name

    def _compute_report_tax(self):
        if self.tax_id:
            temp_tax = list()
            for tax in self.tax_id:
                temp_str = tax.name + " " + str(abs(tax.amount)) + "%"
                temp_tax.append(temp_str)

            self.report_taxes = ", ".join(temp_tax)
        else:
            self.report_taxes = ""

    @api.depends('project.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            pro = rec.project
            scope_ids = []
            if pro.project_scope_ids:
                for line in pro.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

    @api.onchange('start_date', 'end_date')
    def _onchange_total_duration(self):
        for obj in self:
            if obj.start_date != False:
                records = self.env['project.project'].search([("id", "=", obj.project.id)])
                for project in records:
                    if project.start_date and not project.act_start_date:
                        if obj.start_date < project.start_date:
                            raise ValidationError(
                                _("Planned Start Date for this contract vendor must be same or after Planned Start Date selected project"))
                    elif project.start_date and project.act_start_date:
                        if obj.start_date < project.act_start_date:
                            raise ValidationError(
                                _("Planned Start Date for this contract vendor must be same or after Actual Start Date selected project"))
                if obj.end_date != False:
                    if obj.start_date > obj.end_date:
                        raise ValidationError(_("Planned End Date must be same or after Planned Start Date"))
                    if project.end_date:
                        if obj.end_date > project.end_date:
                            raise ValidationError(
                                _("Planned End Date for this contract vendor must be same or before Planned End Date selected project"))

            if obj.start_date != False and obj.end_date != False:
                end_date = str(obj.end_date)
                start_date = str(obj.start_date)
                end = datetime.strptime(end_date, "%Y-%m-%d")
                start = datetime.strptime(start_date, "%Y-%m-%d")
                duration = end - start
                if duration.days >= 0:
                    obj.update({
                        'duration': int(duration.days),
                    })
                else:
                    raise ValidationError(_("Invalid Planned Date"))

    @api.onchange('is_subcontracting', 'addendum_payment_method')
    def onchange_addendum_payment_method(self):
        if self.is_subcontracting == True:
            if self.addendum_payment_method == 'split_payment':
                self.contract_parent_po = False
                self.down_payment_method = 'per'
                self.down_payment = False
                self.retention_1 = False
                self.retention_1_date = False
                self.retention_term_1 = False
                self.retention_2 = False
                self.retention_2_date = False
                self.retention_term_2 = False
                self.tax_id = False
            elif self.addendum_payment_method == 'join_payment':
                self.contract_parent_po = False

    @api.onchange('contract_parent_po')
    def onchange_contract_parent(self):
        if self.contract_parent_po:
            join = self.contract_parent_po
            self.start_date = join.start_date
            self.end_date = join.end_date
            self.down_payment_method = join.down_payment_method
            self.down_payment = join.down_payment
            self.retention_1 = join.retention_1
            self.retention_1_date = join.retention_1_date
            self.retention_term_1 = join.retention_term_1
            self.retention_2 = join.retention_2
            self.retention_2_date = join.retention_2_date
            self.retention_term_2 = join.retention_term_2
            self.tax_id = [(6, 0, [v.id for v in join.tax_id])]
            self.payment_term_id = join.payment_term_id
            self.penalty_id = join.penalty_id
            self.diff_penalty = join.diff_penalty
            self.method = join.method
            self.amount = join.amount
            self.method_client = join.method_client
            self.amount_client = join.amount_client
        else:
            self.down_payment_method = False
            self.down_payment = False
            self.retention_1 = False
            self.retention_1_date = False
            self.retention_term_1 = False
            self.retention_2 = False
            self.retention_2_date = False
            self.retention_term_2 = False
            self.tax_id = False
            self.penalty_id = False
            self.diff_penalty = False
            self.method = False
            self.amount = False
            self.method_client = False
            self.amount_client = False

    @api.onchange('subcon_contract')
    def _get_split_material(self):
        for res in self:
            contract = res.env['purchase.order'].search(
                [('subcon_contract', '=', res.subcon_contract.id), ('project', '=', res.project.id),
                 ('state', 'in', ('purchase', 'done'))])
            for po in res.subcon_contract:
                po.write({'split_po': [(6, 0, contract.ids)],
                          'split_material': True, })

    def _compute_count_contract(self):
        for res in self:
            contract = self.env['purchase.order'].search_count(
                [('contract_parent_po', '=', res.id), ('project', '=', res.project.id),
                 ('state', 'in', ('purchase', 'done'))])
            res.count_contract = contract

    # @api.depends('is_subcontracting', 'sub_contracting')
    # def set_addendum_payment_method(self):
    #     # self.addendum_payment_method = False
    #     if self.is_subcontracting == True:
    #         if self.sub_contracting == 'main_contract':
    #             self.addendum_payment_method = 'split_payment'
    #         else:
    #             self.addendum_payment_method = 'join_payment'
    #     else:
    #         self.addendum_payment_method = False

    # @api.depends('split_material', 'variable_line_ids.budget_amount', 'variable_line_ids.budget_amount_total')
    # def _onchange_split_material(self):
    #     for rec in self:
    #         if rec.project_budget:
    #             if rec.split_material == True:
    #                 for line in rec.variable_line_ids:
    #                     line.budget_amount = line.bd_subcon_id.amount - line.variable.total_variable_material
    #                     line.budget_amount_total = line.budget_amount * line.quantity
    #             else:
    #                 for line in rec.variable_line_ids:
    #                     line.budget_amount = line.bd_subcon_id.amount
    #                     line.budget_amount_total = line.budget_amount * line.quantity
    #         else:
    #             if rec.split_material == True:
    #                 for line in rec.variable_line_ids:
    #                     line.budget_amount = line.cs_subcon_id.price_unit - line.variable.total_variable_material
    #                     line.budget_amount_total = line.budget_amount * line.quantity
    #             else:
    #                 for line in rec.variable_line_ids:
    #                     line.budget_amount = line.cs_subcon_id.price_unit
    #                     line.budget_amount_total = line.budget_amount * line.quantity

    @api.onchange('project', 'partner_id')
    def exist_main_contract_1(self):
        for res in self:
            branch = res.project.branch_id
            main_contract = self.env['purchase.order'].search(
                [('is_subcontracting', '=', True), ('project', '=', res.project.id),
                 ('partner_id', '=', res.partner_id.id), ('sub_contracting', '=', 'main_contract'),
                 ('state', 'in', ('purchase', 'done'))])
            if res.is_subcontracting == True:
                if res.partner_id:
                    if res.project:
                        purc = self.env['purchase.order'].search_count(
                            [('is_subcontracting', '=', True), ('project', '=', res.project.id),
                             ('partner_id', '=', res.partner_id.id), ('sub_contracting', '=', 'main_contract'),
                             ('state', 'in', ('purchase', 'done'))])
                        if purc > 0:
                            res.write({'sub_contracting': 'addendum',
                                       'main_po_reference': main_contract,
                                       'addendum_payment_method': 'join_payment'
                                       })
                        else:
                            res.write({'sub_contracting': 'main_contract',
                                       'main_po_reference': False,
                                       'addendum_payment_method': 'split_payment'
                                       })
            if branch:
                res.branch_id = res.project.branch_id.id
            else:
                res.branch_id = False

    @api.onchange('discounted_total')
    def onchange_contract_amount_to_join(self):
        for res in self:
            if res.sub_contracting == 'addendum':
                if res.discounted_total > 0:
                    res.addendum_payment_method = 'split_payment' 
                else:
                    res.addendum_payment_method = 'join_payment' 

    @api.depends('down_payment_method', 'down_payment', 'discounted_total')
    def _compute_total_downpayment(self):
        for res in self:
            if res.down_payment_method == 'per':
                res.dp_amount = res.discounted_total * (res.down_payment / 100)
            elif res.down_payment_method == 'fix':
                res.dp_amount = res.down_payment
            else:
                res.dp_amount = 0

    @api.onchange('project')
    def _onchange_project(self):
        for rec in self:
            for proj in rec.project:
                self.cost_sheet = rec.env['job.cost.sheet'].search(
                    [('project_id', '=', proj.id), ('state', '!=', 'cancelled')])
                self.analytic_account_group_ids = proj.analytic_idz
                self.destination_warehouse_id = proj.warehouse_address

    @api.onchange('project', 'destination_warehouse_id', 'is_single_delivery_destination')
    def _onchange_destination_warehouse(self):
        res = super(RequestForQuotations, self)._onchange_destination_warehouse()
        if len(self.project) > 0:
            self.destination_warehouse_id = self.project.warehouse_address
        return res

    # Subcon
    def validate_amount(self, rec):
        if rec.total == 0:
            raise ValidationError(("The unit price is empty, please fill the unit price"))
        else:
            return rec

    def validate_budget(self, rec):
        if rec.quantity > rec.budget_quantity:
            raise ValidationError(("The quantity is over the budget quantity"))
        elif rec.total > rec.budget_amount_total:
            raise ValidationError(("The total amount is over the budget amount left"))
        else:
            return rec

    # Product
    def validate_line_amount(self, line):
        if line.price_subtotal == 0:
            raise ValidationError(("The unit price is empty, please fill the unit price"))
        else:
            return line

    def validate_line_budget(self, line):
        if self.budgeting_method == 'product_budget':
            if line.product_qty > line.budget_quantity:
                raise ValidationError(("The quantity is over the budget quantity"))
            elif line.price_subtotal > line.remining_budget_amount:
                raise ValidationError(("The total amount is over the budget amount left"))
            else:
                return line
        else:
            return line

    def validate_budget_total(self):
        if self.budgeting_method == 'total_budget':
            if self.project_budget:
                if self.amount_total > self.project_budget.budget_left:
                    raise ValidationError(("The total is over the amount budget left"))
            else:
                if self.amount_total > self.cost_sheet.contract_budget_left:
                    raise ValidationError(("The total is over the amount budget left"))

    def validate_type_budget(self, total_mat, total_lab, total_ove, total_equ, total_split, line):
        if line.type == 'material':
            total_mat += line.price_subtotal
            if self.project_budget:
                if total_mat > self.project_budget.amount_left_material:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.project_budget.amount_left_material * (self.cost_sheet.ratio_value / 100)) + self.project_budget.amount_left_material
                        if total_mat > over_budget_limit:
                            raise ValidationError(_("Limit for Material is '%s'" % over_budget_limit))
                    return True
            else:
                if total_mat > self.cost_sheet.material_budget_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.cost_sheet.material_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.material_budget_left
                        if total_mat> over_budget_limit:
                            raise ValidationError(_("Limit for Material is '%s'" % over_budget_limit))
                    return True
        elif line.type == 'labour':
            total_lab += line.price_subtotal
            if self.project_budget:
                if total_lab > self.project_budget.amount_left_labour:
                    raise ValidationError(("The labour total is over the labour amount budget left"))
            else:
                if total_lab > self.cost_sheet.labour_budget_left:
                    raise ValidationError(("The labour total is over the labour amount budget left"))
        elif line.type == 'overhead':
            total_ove += line.price_subtotal
            if self.project_budget:
                if total_ove > self.project_budget.amount_left_overhead:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.project_budget.amount_left_overhead * (
                                    self.cost_sheet.ratio_value / 100)) + self.project_budget.amount_left_overhead
                        if total_ove > over_budget_limit:
                            raise ValidationError(_("Limit for Overhead is '%s'" % over_budget_limit))
                    return True
            else:
                if total_ove > self.cost_sheet.overhead_budget_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.cost_sheet.overhead_budget_left * (
                                    self.cost_sheet.ratio_value / 100)) + self.cost_sheet.overhead_budget_left
                        if total_ove > over_budget_limit:
                            raise ValidationError(_("Limit for Overhead is '%s'" % over_budget_limit))
                    return True
        elif line.type == 'equipment':
            total_equ += line.price_subtotal
            if self.project_budget:
                if total_equ > self.project_budget.amount_left_equipment:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.project_budget.amount_left_equipment * (
                                self.cost_sheet.ratio_value / 100)) + self.project_budget.amount_left_equipment
                        if total_equ > over_budget_limit:
                            raise ValidationError(_("Limit for Overhead is '%s'" % over_budget_limit))
                    return True
            else:
                if total_equ > self.cost_sheet.equipment_budget_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.cost_sheet.equipment_budget_left * (
                                self.cost_sheet.ratio_value / 100)) + self.cost_sheet.equipment_budget_left
                        if total_equ > over_budget_limit:
                            raise ValidationError(_("Limit for Equipment is '%s'" % over_budget_limit))
                    return True
        elif line.type == 'split':
            total_split += line.price_subtotal
            if self.project_budget:
                if total_split > self.project_budget.amount_left_subcon:
                    return True
            else:
                if total_split > self.cost_sheet.subcon_budget_left:
                    return True

        return False

    # Subcon
    # update
    
    def create_subcon_task(self, rec):
        for res in self:
            project_task = res.env['project.task']
            if res.sub_contracting == 'main_contract':
                project_task.create({
                    'name': rec.project_scope.name + ' - ' + rec.section.name + ' - ' + rec.variable.name,
                    'is_subcon': True,
                    'project_id': res.project.id,
                    'cost_sheet': res.cost_sheet.id,
                    'project_director': res.project.project_director.id,
                    'completion_ref': self.env['project.completion.const'].search(
                                         [('completion_id', '=', res.project.id), ('name', '=', res.contract_customer.id)], limit=1).id,
                    'purchase_subcon': res.id,
                    'sale_order': res.contract_customer.id,
                    'sub_contractor': res.partner_id.id,
                    'cs_subcon_id': rec.cs_subcon_id.id,
                    'bd_subcon_id': rec.bd_subcon_id.id,
                    'po_subcon_id': rec.id,
                    'work_subcon_weightage': rec.dp_amount_percentage * 100,
                    'planned_start_date': res.start_date,
                    'planned_end_date': res.end_date,
                })
            else:
                if res.discounted_total > 0:
                    project_task.create({
                        'name': 'Addendum - ' + rec.project_scope.name + ' - ' + rec.section.name + ' - ' + rec.variable.name,
                        'is_subcon': True,
                        'project_id': res.project.id,
                        'cost_sheet': res.cost_sheet.id,
                        'project_director': res.project.project_director.id,
                        'purchase_subcon': res.id,
                        'completion_ref': self.env['project.completion.const'].search(
                            [('completion_id', '=', res.project.id), ('name', '=', res.contract_customer.id)],
                            limit=1).id,
                        'sub_contractor': res.partner_id.id,
                        'cs_subcon_id': rec.cs_subcon_id.id,
                        'bd_subcon_id': rec.bd_subcon_id.id,
                        'po_subcon_id': rec.id,
                        'work_subcon_weightage': rec.dp_amount_percentage * 100,
                        'planned_start_date': res.start_date,
                        'planned_end_date': res.end_date,
                    })

    def update_amount_cost_sheet(self, line):
        for cs in line.cs_subcon_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_amount)
            reserved_return_amount = (estimated_budget_amount - line.total) if estimated_budget_amount > line.total else 0
            reserved_over_amount = (estimated_budget_amount - line.total) if estimated_budget_amount < line.total else 0

            cs.reserved_amt += line.total
            cs.po_reserved_qty += line.quantity
            cs.reserved_return_amount += reserved_return_amount
            cs.reserved_over_amount += abs(reserved_over_amount)

        return line

    def update_amount_project_budget(self, line):
        for sub in line.bd_subcon_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_amount)
            reserved_return_amount = (estimated_budget_amount - line.total) if estimated_budget_amount > line.total else 0
            reserved_over_amount = (estimated_budget_amount - line.total) if estimated_budget_amount < line.total else 0

            sub.amt_res += line.total
            sub.po_reserved_qty += line.quantity
            sub.reserved_return_amount += reserved_return_amount
            sub.reserved_over_amount += abs(reserved_over_amount)

        return line

    def update_amount_cost_sheet_type(self, rec):
        if self.total > self.cost_sheet.subcon_budget_left:
            raise ValidationError(("The total is over the amount budget left"))
        else:
            for cs in rec.cs_subcon_id:
                reserved = (cs.reserved_amt + rec.total)
                for cos in self.cost_sheet:
                    cos.material_subcon_ids = [(1, rec.cs_subcon_id.id, {
                        'reserved_amt': reserved,
                    })]

            return rec

    def update_amount_project_budget_type(self, rec):
        if self.total > self.project_budget.amount_left_subcon:
            raise ValidationError(("The total is over the amount budget left"))
        else:
            for sub in rec.bd_subcon_id:
                reserved = (sub.amt_res + rec.total)
                for bud in self.project_budget:
                    bud.budget_subcon_ids = [(1, rec.bd_subcon_id.id, {
                        'amt_res': reserved,
                    })]
                
            return rec

    def update_amount_cost_sheet_total(self, rec):
        if self.total > self.cost_sheet.contract_budget_left:
            raise ValidationError(("The total is over the amount budget left"))
        else:
            for cs in rec.cs_subcon_id:
                reserved = (cs.reserved_amt + rec.total)
                for cos in self.cost_sheet:
                    cos.material_subcon_ids = [(1, rec.cs_subcon_id.id, {
                        'reserved_amt': reserved,
                    })]

            return rec

    def update_amount_project_budget_total(self, rec):
        if self.total > self.project_budget.budget_left:
            raise ValidationError(("The total is over the amount budget left"))
        else:
            for sub in rec.bd_subcon_id:
                reserved = (sub.amt_res + rec.total)
                for bud in self.project_budget:
                    bud.budget_subcon_ids = [(1, rec.bd_subcon_id.id, {
                        'amt_res': reserved,
                    })]
                
            return rec

        # cancel

    def cancel_amount_cost_sheet(self, rec):

        for cs in rec.cs_subcon_id:
            estimated_budget_amount = (rec.budget_quantity * rec.budget_amount)
            reserved_over_amount = (estimated_budget_amount - rec.total) if estimated_budget_amount < rec.total else 0
            reserved_return_amount = (estimated_budget_amount - rec.total) if estimated_budget_amount > rec.total else 0

            cs.reserved_over_amount -= abs(reserved_over_amount)
            cs.reserved_return_amount -= reserved_return_amount
            cs.po_reserved_qty -= rec.quantity

            cs.reserved_amt -= rec.total
        return rec

    def cancel_amount_project_budget(self, rec):
        for sub in rec.bd_subcon_id:
            estimated_budget_amount = (rec.budget_quantity * rec.budget_amount)
            reserved_over_amount = (estimated_budget_amount - rec.total) if estimated_budget_amount < rec.total else 0
            reserved_return_amount = (estimated_budget_amount - rec.total) if estimated_budget_amount > rec.total else 0

            sub.reserved_over_amount -= abs(reserved_over_amount)
            sub.reserved_return_amount -= reserved_return_amount
            sub.po_reserved_qty -= rec.quantity
            sub.amt_res -= rec.total
        return rec

    def cancel_amount_cost_sheet_type(self, rec):
        for cs in self.cost_sheet:
            cs.subcon_budget_res -= rec.total
            rec.cs_subcon_id.reserved_amt -= rec.total
        return rec

    def cancel_amount_project_budget_type(self, rec):
        for sub in self.project_budget:
            sub.amount_reserved_subcon -= rec.total
            rec.bd_subcon_id.amt_res -= rec.total
        return rec

    def cancel_amount_cost_sheet_total(self, rec):
        for cs in self.cost_sheet:
            cs.contract_budget_res -= rec.total
        return rec

    def cancel_amount_project_budget_total(self, rec):
        for sub in self.project_budget:
            pass
        return rec

    # update contract
    def update_contract(self):
        if self.is_subcontracting == True:
            if self.sub_contracting == 'main_contract':
                self.write({'contract_parent_po': self.id,
                            'related_contract_ids': [(6, 0, self.ids)],
                            })
            elif self.sub_contracting == 'addendum':
                if self.addendum_payment_method == 'split_payment':
                    self.write({'contract_parent_po': self.id,
                                'related_contract_ids': [(6, 0, self.ids)],
                                })
                elif self.addendum_payment_method == 'join_payment':
                    if self.contract_parent_po:
                        res = self.contract_parent_po
                        res.write({'related_contract_ids': [(4, self.id)]})

    def _main_contract_data(self):
        return {
            'name': self.id,
            'order_date': datetime.now(),
            'project_id': self.project.id,
            'subcon_down_payment': self.down_payment,
            'subcon_dp_method': self.down_payment_method,
            # 'subcon_dp_amount': self.dp_amount,
            'subcon_retention1': self.retention_1,
            'subcon_retention1_date': self.retention_1_date,
            'subcon_retention_term_1': self.retention_term_1.id,
            'subcon_retention2': self.retention_2,
            'subcon_retention2_date': self.retention_2_date,
            'subcon_retention_term_2': self.retention_term_2.id,
            'subcon_tax_id': self.tax_id,
            'subcon_payment_term': self.payment_term_id.id,
            'subcon_contract_amount': self.total_all,
            'partner_id': self.partner_id.id,
            'diff_penalty': self.diff_penalty,
            'amount': self.amount,
            'method': self.method,
            'amount_client': self.amount_client,
            'method_client': self.method_client,
        }

    def _variation_order_data(self, contract):
        return {
            'contract_id': contract.id,
            'name': self.id,
            'order_date': datetime.now(),
            'project_id': self.project.id,
            'down_payment': self.down_payment,
            'dp_method': self.down_payment_method,
            'retention1': self.retention_1,
            'retention1_date': self.retention_1_date,
            'retention_term_1': self.retention_term_1.id,
            'retention2': self.retention_2,
            'retention2_date': self.retention_2_date,
            'retention_term_2': self.retention_term_2.id,
            'tax_id': self.tax_id,
            'payment_term': self.payment_term_id.id,
            'vo_payment_type': self.addendum_payment_method,
            'contract_amount': self.total_all,
            'partner_id': self.partner_id.id,
            'diff_penalty': self.diff_penalty,
            'amount': self.amount,
            'method': self.method,
            'amount_client': self.amount_client,
            'method_client': self.method_client,
        }

    def create_contract_subcon(self):
        if self.sub_contracting == 'main_contract':
            self.project.contract_subcon_ids.create(self._main_contract_data())
        else:
            contract = self.project.contract_subcon_ids.filtered(lambda x: x.partner_id == self.partner_id and
                                                                           x.state in ('purchase', 'done'))
            contract.variation_subcon_ids.create(self._variation_order_data(contract))

    # Product
    # update
    def update_line_material_cs(self, line):
        for cs in line.cs_material_id:
            # reserved = (cs.reserved_amt + line.price_subtotal)
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
            reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0
            reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
            # for cos in self.cost_sheet:
            #     cos.material_ids = [(1, line.cs_material_id.id, {
            #         'reserved_amt': reserved,
            #     })]
            cs.reserved_amt += line.price_subtotal
            cs.po_reserved_qty += line.product_qty
            cs.reserved_return_amount += reserved_return_amount
            cs.reserved_over_amount += abs(reserved_over_amount)

        line.cs_material_gop_id.reserved_amt += line.price_subtotal
        return line
        
    def update_line_material_bd(self, line):
        for material in line.bd_material_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
            reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0
            reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0

            material.amt_res += line.price_subtotal
            material.po_reserved_qty += line.product_qty
            material.reserved_return_amount += reserved_return_amount
            material.reserved_over_amount += abs(reserved_over_amount)
        line.bd_material_gop_id.amt_res += line.price_subtotal
        return line
        
    def update_line_labour_cs(self, line):
        for cs in line.cs_labour_id:
            reserved = (cs.reserved_amt + line.price_subtotal)
            for cos in self.cost_sheet:
                cos.material_labour_ids = [(1, line.cs_labour_id.id, {
                    'reserved_amt': reserved,
                })]
        line.cs_labour_gop_id.reserved_amt += line.price_subtotal
        return line

    def update_line_labour_bd(self, line):
        for sub in line.bd_labour_id:
            reserved = (sub.amt_res + line.price_subtotal)
            for bud in self.project_budget:
                bud.budget_labour_ids = [(1, line.bd_labour_id.id, {
                    'amt_res': reserved,
                })]
        line.bd_labour_gop_id.amt_res += line.price_subtotal
        return line

    def update_line_overhead_cs(self, line):
        for cs in line.cs_overhead_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
            reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0
            reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0

            cs.reserved_amt += line.price_subtotal
            cs.po_reserved_qty += line.product_qty
            cs.reserved_return_amount += reserved_return_amount
            cs.reserved_over_amount += abs(reserved_over_amount)
        line.cs_overhead_gop_id.reserved_amt += line.price_subtotal
        return line

    def update_line_overhead_bd(self, line):
        for overhead in line.bd_overhead_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
            reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0
            reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0

            overhead.amt_res += line.price_subtotal
            overhead.po_reserved_qty += line.product_qty
            overhead.reserved_return_amount += reserved_return_amount
            overhead.reserved_over_amount += abs(reserved_over_amount)
        line.bd_overhead_gop_id.amt_res += line.price_subtotal
        return line

    def update_line_equipment_cs(self, line):
        for cs in line.cs_equipment_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
            reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0
            reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0

            cs.reserved_amt += line.price_subtotal
            cs.po_reserved_qty += line.product_qty
            cs.reserved_return_amount += reserved_return_amount
            cs.reserved_over_amount += abs(reserved_over_amount)
        line.cs_equipment_gop_id.reserved_amt += line.price_subtotal
        return line

    def update_line_equipment_bd(self, line):
        for equipment in line.bd_equipment_id:
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
            reserved_return_amount = (
                        estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0
            reserved_over_amount = (
                        estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0

            equipment.amt_res += line.price_subtotal
            equipment.po_reserved_qty += line.product_qty
            equipment.reserved_return_amount += reserved_return_amount
            equipment.reserved_over_amount += abs(reserved_over_amount)

        line.bd_equipment_gop_id.amt_res += line.price_subtotal
        return line

    def update_line_subcon_cs(self, line):
        for cs in line.cs_subcon_id:
            reserved = (cs.reserved_amt + line.price_subtotal)
            for cos in self.cost_sheet:
                cos.material_subcon_ids = [(1, line.cs_subcon_id.id, {
                    'reserved_amt': reserved,
                })]
        return line
    
    def update_line_subcon_bd(self, line):
        for sub in line.bd_subcon_id:
            reserved = (sub.amt_res + line.price_subtotal)
            for bud in self.project_budget:
                bud.budget_subcon_ids = [(1, line.bd_subcon_id.id, {
                    'amt_res': reserved,
                })]
        return line

        # cancel

    def cancel_line_material_cs(self, line):
        estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
        reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
        reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0

        line.cs_material_id.reserved_over_amount -= abs(reserved_over_amount)
        line.cs_material_id.reserved_return_amount -= reserved_return_amount
        line.cs_material_id.po_reserved_qty -= line.product_qty

        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for cs in line.cs_material_id:
                cs.reserved_amt -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type':
            line.cs_material_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.material_budget_res -= line.price_subtotal
            return line
        else:
            line.cs_material_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.material_budget_res -= line.price_subtotal
            return line

    def cancel_line_material_bd(self, line):
        estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
        reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
        reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0

        line.bd_material_id.reserved_over_amount -= abs(reserved_over_amount)
        line.bd_material_id.reserved_return_amount -= reserved_return_amount
        line.bd_material_id.po_reserved_qty -= line.product_qty

        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for sub in line.bd_material_id:
                sub.amt_res -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type':
            line.bd_material_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_material -= line.price_subtotal
            return line
        else:
            line.bd_material_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_material -= line.price_subtotal
            return line

    def cancel_line_labour_cs(self, line):
        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for cs in line.cs_labour_id:
                cs.reserved_amt -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type' or self.budgeting_method == 'gop_budget':
            line.cs_labour_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.labour_budget_res -= line.price_subtotal
            return line
        else:
            line.cs_labour_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.labour_budget_res -= line.price_subtotal
            return line

    def cancel_line_labour_bd(self, line):
        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for sub in line.bd_labour_id:
                sub.amt_res -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type' or self.budgeting_method == 'gop_budget':
            line.bd_labour_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_labour -= line.price_subtotal
            return line
        else:
            line.bd_labour_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_labour -= line.price_subtotal
            return line

    def cancel_line_overhead_cs(self, line):
        estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
        reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
        reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0

        line.cs_overhead_id.reserved_over_amount -= abs(reserved_over_amount)
        line.cs_overhead_id.reserved_return_amount -= reserved_return_amount
        line.cs_overhead_id.po_reserved_qty -= line.product_qty

        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for cs in line.cs_overhead_id:
                cs.reserved_amt -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type' or self.budgeting_method == 'gop_budget':
            line.cs_overhead_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.overhead_budget_res -= line.price_subtotal
            return line
        else:
            line.cs_overhead_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.overhead_budget_res -= line.price_subtotal
            return line

    def cancel_line_overhead_bd(self, line):
        estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
        reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
        reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0

        line.bd_overhead_id.reserved_over_amount -= abs(reserved_over_amount)
        line.bd_overhead_id.reserved_return_amount -= reserved_return_amount
        line.bd_overhead_id.po_reserved_qty -= line.product_qty

        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for sub in line.bd_overhead_id:
                sub.amt_res -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type' or self.budgeting_method == 'gop_budget':
            line.bd_overhead_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_overhead -= line.price_subtotal
            return line
        else:
            line.bd_overhead_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_overhead -= line.price_subtotal
            return line

    def cancel_line_equipment_cs(self, line):
        estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
        reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
        reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0

        line.cs_equipment_id.reserved_over_amount -= abs(reserved_over_amount)
        line.cs_equipment_id.reserved_return_amount -= reserved_return_amount
        line.cs_equipment_id.po_reserved_qty -= line.product_qty

        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for cs in line.cs_equipment_id:
                cs.reserved_amt -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type':
            line.cs_equipment_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.equipment_budget_res -= line.price_subtotal
            return line
        else:
            line.cs_equipment_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.equipment_budget_res -= line.price_subtotal
            return line

    def cancel_line_equipment_bd(self, line):
        estimated_budget_amount = (line.budget_quantity * line.budget_unit_price)
        reserved_over_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount < line.price_subtotal else 0
        reserved_return_amount = (estimated_budget_amount - line.price_subtotal) if estimated_budget_amount > line.price_subtotal else 0

        line.bd_equipment_id.reserved_over_amount -= abs(reserved_over_amount)
        line.bd_equipment_id.reserved_return_amount -= reserved_return_amount
        line.bd_equipment_id.po_reserved_qty -= line.product_qty

        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for sub in line.bd_equipment_id:
                sub.amt_res -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type':
            line.bd_equipment_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_overhead -= line.price_subtotal
            return line
        else:
            line.bd_equipment_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_overhead -= line.price_subtotal
            return line

    def cancel_line_subcon_cs(self, line):
        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for cs in line.cs_subcon_id:
                cs.reserved_amt -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type':
            line.cs_subcon_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.subcon_budget_res -= line.price_subtotal
            return line
        else:
            line.cs_subcon_id.reserved_amt -= line.price_subtotal
            for cost in self.cost_sheet:
                cost.subcon_budget_res -= line.price_subtotal
            return line

    def cancel_line_subcon_bd(self, line):
        if self.budgeting_method == 'product_budget' or self.budgeting_method == 'gop_budget':
            for sub in line.bd_subcon_id:
                sub.amt_res -= line.price_subtotal
            return line
        elif self.budgeting_method == 'budget_type':
            line.bd_subcon_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_overhead -= line.price_subtotal
            return line
        else:
            line.bd_subcon_id.amt_res -= line.price_subtotal
            for bd in self.project_budget:
                bd.amount_reserved_overhead -= line.price_subtotal
            return line

    def validate_gop_budget(self, mat_recs, lab_recs, ove_recs, equ_recs, split_recs, line):
        if line.type == 'material':
            gop_mat_group = str(line.project_scope.id) + str(line.section.id) + str(line.group_of_product.id)
            if gop_mat_group in mat_recs:
                mat_recs[gop_mat_group]['amount'] += line.price_subtotal
            else:
                mat_recs[gop_mat_group] = {}
                mat_recs[gop_mat_group]['amount'] = line.price_subtotal
            if self.project_budget:
                if mat_recs[gop_mat_group]['amount'] > line.bd_material_gop_id.amt_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (line.bd_material_gop_id.amt_left * (self.cost_sheet.ratio_value / 100)) + line.bd_material_gop_id.amt_left
                        if mat_recs[gop_mat_group]['amount'] > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (line.group_of_product.name, over_budget_limit)))
                    return True
            else:
                if mat_recs[gop_mat_group]['amount'] > line.cs_material_gop_id.budgeted_amt_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (line.cs_material_gop_id.budgeted_amt_left * (self.cost_sheet.ratio_value / 100)) + line.cs_material_gop_id.budgeted_amt_left
                        if mat_recs[gop_mat_group]['amount'] > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (line.group_of_product.name, over_budget_limit)))
                    return True

        elif line.type == 'labour':
            gop_lab_group = str(line.project_scope.id) + str(line.section.id) + str(line.group_of_product.id)
            if gop_lab_group in lab_recs:
                lab_recs[gop_lab_group]['amount'] += line.price_subtotal
            else:
                lab_recs[gop_lab_group] = {}
                lab_recs[gop_lab_group]['amount'] = line.price_subtotal
            if self.project_budget:
                if lab_recs[gop_lab_group]['amount'] > line.bd_labour_gop_id.amt_left:
                    raise ValidationError(("The labour total is over the group of product labour amount budget left"))
            else:
                if lab_recs[gop_lab_group]['amount'] > line.cs_labour_gop_id.budgeted_amt_left:
                    raise ValidationError(("The labour total is over the group of product labour amount budget left"))
        elif line.type == 'overhead':
            gop_ove_group = str(line.project_scope.id) + str(line.section.id) + str(line.group_of_product.id)
            if gop_ove_group in ove_recs:
                ove_recs[gop_ove_group]['amount'] += line.price_subtotal
            else:
                ove_recs[gop_ove_group] = {}
                ove_recs[gop_ove_group]['amount'] = line.price_subtotal
            if self.project_budget:
                if ove_recs[gop_ove_group]['amount'] > line.bd_overhead_gop_id.amt_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (line.bd_overhead_gop_id.amt_left * (self.cost_sheet.ratio_value / 100)) + line.bd_overhead_gop_id.amt_left
                        if ove_recs[gop_ove_group]['amount'] > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (line.group_of_product.name, over_budget_limit)))
                    return True
            else:
                if ove_recs[gop_ove_group]['amount'] > line.cs_overhead_gop_id.budgeted_amt_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (line.cs_overhead_gop_id.budgeted_amt_left * (self.cost_sheet.ratio_value / 100)) + line.cs_overhead_gop_id.budgeted_amt_left
                        if ove_recs[gop_ove_group]['amount'] > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (line.group_of_product.name, over_budget_limit)))
                    return True
        elif line.type == 'equipment':
            gop_equ_group = str(line.project_scope.id) + str(line.section.id) + str(line.group_of_product.id)
            if gop_equ_group in equ_recs:
                equ_recs[gop_equ_group]['amount'] += line.price_subtotal
            else:
                equ_recs[gop_equ_group] = {}
                equ_recs[gop_equ_group]['amount'] = line.price_subtotal
            if self.project_budget:
                if equ_recs[gop_equ_group]['amount'] > line.bd_equipment_gop_id.amt_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (line.bd_equipment_gop_id.amt_left * (self.cost_sheet.ratio_value / 100)) + line.bd_equipment_gop_id.amt_left
                        if equ_recs[gop_equ_group]['amount'] > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (line.group_of_product.name, over_budget_limit)))
                    return True
            else:
                if equ_recs[gop_equ_group]['amount'] > line.cs_equipment_gop_id.budgeted_amt_left:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (line.cs_equipment_gop_id.budgeted_amt_left * (self.cost_sheet.ratio_value / 100)) + line.cs_equipment_gop_id.budgeted_amt_left
                        if equ_recs[gop_equ_group]['amount'] > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (line.group_of_product.name, over_budget_limit)))
                    return True
        elif line.type == 'split':
            sub_id_group = str(line.project_scope.id) + str(line.section.id) + str(line.group_of_product.id)
            if sub_id_group in split_recs:
                split_recs[sub_id_group]['amount'] += line.price_subtotal
            else:
                split_recs[sub_id_group] = {}
                split_recs[sub_id_group]['amount'] = line.price_subtotal
            if self.project_budget:
                if split_recs[sub_id_group]['amount'] > line.bd_subcon_id.amt_left:

                    return True
            else:
                if split_recs[sub_id_group]['amount'] > line.cs_subcon_id.budgeted_amt_left:
                    return True

        return False

    def action_job_order_subcon(self):
        tree_view = self.env.ref('equip3_construction_masterdata.view_task_tree_project').id
        return {
            'name': ("Job Orders Subcon"),
            'views': [(tree_view, "tree"), (False, "form")],
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'context': {'default_project_id': self.project.id,
                        'default_purchase_subcon': self.id,
                        'default_is_subcon': True},
            'target': 'current',
            'domain': [('project_id', '=', self.project.id), 
                       ('purchase_subcon', '=', self.id),
                       ('is_subcon', '=', True)],
        }

    def create_blanket_order(self):
        res = super(RequestForQuotations, self).create_blanket_order()

        for rec in self:
            if rec.project:
                blanket_order = rec.env['purchase.requisition'].search([('origin', '=', rec.name)], limit=1)
                if blanket_order:
                    if rec.project_budget:
                        vals = {
                            'project_id': rec.project.id,
                            'cost_sheet_id': rec.cost_sheet.id,
                            'project_budget_id': rec.project_budget.id,
                        }
                    else:
                        vals = {
                            'project_id': rec.project.id,
                            'cost_sheet_id': rec.cost_sheet.id,
                        }
                    blanket_order.write(vals)

        return res

    def return_over_budget_confirmation(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warning',
            'res_model': 'purchase.order.over.budget.validation.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_order_id': self.id,
                        }
        }

    def create_subcon(self):
        for record in self:
            for rec in record.variable_line_ids:
                record.validate_amount(rec)
                if record.project_budget:
                    record.update_amount_cost_sheet(rec)
                    record.update_amount_project_budget(rec)
                    record.create_subcon_task(rec)
                else:
                    record.update_amount_cost_sheet(rec)
                    record.create_subcon_task(rec)
            record.update_contract()
            record.create_contract_subcon()

    def button_confirm(self):
        if self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            if self.is_subcontracting == True:
                if self.retention_1 > 0 and self.retention_term_1 == False:
                    raise ValidationError(_("You haven't set Retention 1 Date for this contract"))

                if self.retention_2 > 0 and self.retention_term_2 == False:
                    raise ValidationError(_("You haven't set Retention 2 Date for this contract"))

                if self.use_dp == True and self.down_payment == 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'confirm.downpayment.purchase',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                    }
                elif self.use_retention == True and self.retention_1 == 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'confirm.retention.purchase',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                    }
                else:

                    res = super(RequestForQuotations, self).button_confirm()
                    self.create_subcon()
                    return res
            else:

                total_mat = 0.00
                total_lab = 0.00
                total_ove = 0.00
                total_equ = 0.00
                total_split = 0.00
                mat_recs = {}
                lab_recs = {}
                ove_recs = {}
                equ_recs = {}
                split_recs = {}
                # Split validation loop and update value loop
                # to prevent early update value resulting double value in first line of PO
                # If you have better solution, you can refactor this code
                if self.budgeting_method == 'total_budget':
                    if self.project_budget:
                        if self.amount_untaxed > self.project_budget.budget_left and not self.is_continue_over_budget:
                            if self.cost_sheet.is_over_budget_ratio:
                                over_budget_limit = (self.project_budget.budget_left * (self.cost_sheet.ratio_value/100)) + self.project_budget.budget_left
                                if self.amount_untaxed > over_budget_limit:
                                    raise ValidationError(_("Limit for this project is '%s'" % over_budget_limit))
                            return{
                                'type': 'ir.actions.act_window',
                                'name': 'Warning',
                                'res_model': 'purchase.order.over.budget.validation.wizard',
                                'view_type': 'form',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': {'default_purchase_order_id': self.id,
                                            }
                            }
                    else:
                        if self.amount_untaxed > self.cost_sheet.contract_budget_left and not self.is_continue_over_budget:
                            if self.cost_sheet.is_over_budget_ratio:
                                over_budget_limit = (self.cost_sheet.contract_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.contract_budget_left
                                if self.amount_untaxed > over_budget_limit:
                                    raise ValidationError(_("Limit for this project is '%s'" % over_budget_limit))
                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'Warning',
                                'res_model': 'purchase.order.over.budget.validation.wizard',
                                'view_type': 'form',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': {'default_purchase_order_id': self.id,
                                            }
                            }
                elif self.budgeting_method == 'product_budget' and not self.is_continue_over_budget:
                    for line in self.order_line:
                        if line.price_subtotal > line.remining_budget_amount:
                            if self.cost_sheet.is_over_budget_ratio:
                                over_budget_limit = (line.remining_budget_amount * (self.cost_sheet.ratio_value / 100)) + line.remining_budget_amount
                                if line.price_subtotal > over_budget_limit:
                                    raise ValidationError(_("Limit for '%s' is '%s'" % (line.product_id.name, over_budget_limit)))
                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'Warning',
                                'res_model': 'purchase.order.over.budget.validation.wizard',
                                'view_type': 'form',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': {'default_purchase_order_id': self.id,
                                            }
                            }
                elif self.budgeting_method == 'gop_budget' and not self.is_continue_over_budget:
                    for line in self.order_line:
                        is_over_budget = False
                        is_over_budget = self.validate_gop_budget(mat_recs, lab_recs, ove_recs, equ_recs, split_recs, line)
                        if is_over_budget:
                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'Warning',
                                'res_model': 'purchase.order.over.budget.validation.wizard',
                                'view_type': 'form',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': {'default_purchase_order_id': self.id,
                                            }
                            }
                elif self.budgeting_method == 'budget_type' and not self.is_continue_over_budget:
                    for line in self.order_line:
                        is_over_budget = False
                        is_over_budget = self.validate_type_budget(total_mat, total_lab, total_ove, total_equ, total_split, line)
                        if is_over_budget:
                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'Warning',
                                'res_model': 'purchase.order.over.budget.validation.wizard',
                                'view_type': 'form',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': {'default_purchase_order_id': self.id,
                                            }
                            }

                for line in self.order_line:
                    self.validate_line_amount(line)
                    if line.type == 'material':
                        if self.project_budget:
                            self.update_line_material_cs(line)
                            self.update_line_material_bd(line)
                        else:
                            self.update_line_material_cs(line)
                    elif line.type == 'labour':
                        if self.project_budget:
                            self.update_line_labour_cs(line)
                            self.update_line_labour_bd(line)
                        else:
                            self.update_line_labour_cs(line)
                    elif line.type == 'overhead':
                        if self.project_budget:
                            self.update_line_overhead_cs(line)
                            self.update_line_overhead_bd(line)
                        else:
                            self.update_line_overhead_cs(line)
                    elif line.type == 'equipment':
                        if self.project_budget:
                            self.update_line_equipment_cs(line)
                            self.update_line_equipment_bd(line)
                        else:
                            self.update_line_equipment_cs(line)
                    elif line.type == 'split':
                        if self.project_budget:
                            self.update_line_subcon_cs(line)
                            self.update_line_subcon_bd(line)
                        else:
                            self.update_line_subcon_cs(line)
                    
                    line.is_reserved = True
                res = super(RequestForQuotations, self).button_confirm()
                return res

    def sh_cancel(self):
        res = super(RequestForQuotations, self).sh_cancel()
        if self.is_subcontracting:
            for rec in self.variable_line_ids:
                if rec.is_reserved:
                    if self.project_budget:
                        self.cancel_amount_cost_sheet(rec)
                        self.cancel_amount_project_budget(rec)
                    else:
                        self.cancel_amount_cost_sheet(rec)
            return res
        else:
            cost_sheet = False
            budget = False
            for line in self.order_line:
                if line.is_reserved:
                    if line.type == 'material':
                        if self.project_budget:
                            self.cancel_line_material_cs(line)
                            self.cancel_line_material_bd(line)
                        else:
                            self.cancel_line_material_cs(line)
                        if not cost_sheet:
                            cost_sheet = line.cs_material_id.job_sheet_id
                        if not budget:
                            budget = line.bd_material_id.budget_id
                    elif line.type == 'labour':
                        if self.project_budget:
                            self.cancel_line_labour_cs(line)
                            self.cancel_line_labour_bd(line)
                        else:
                            self.cancel_line_labour_cs(line)
                    elif line.type == 'overhead':
                        if self.project_budget:
                            self.cancel_line_overhead_cs(line)
                            self.cancel_line_overhead_bd(line)
                        else:
                            self.cancel_line_overhead_cs(line)
                        if not cost_sheet:
                            cost_sheet = line.cs_overhead_id.job_sheet_id
                        if not budget:
                            budget = line.bd_overhead_id.budget_id
                    elif line.type == 'equipment':
                        if self.project_budget:
                            self.cancel_line_equipment_cs(line)
                            self.cancel_line_equipment_bd(line)
                        else:
                            self.cancel_line_equipment_cs(line)
                        if not cost_sheet:
                            cost_sheet = line.cs_equipment_id.job_sheet_id
                        if not budget:
                            budget = line.bd_equipment_id.budget_id

            if cost_sheet:
                cost_sheet.get_gop_material_table()
                cost_sheet.get_gop_labour_table()
                cost_sheet.get_gop_overhead_table()
                cost_sheet.get_gop_equipment_table()
            if budget:
                budget.get_gop_material_table()
                budget.get_gop_labour_table()
                budget.get_gop_overhead_table()
                budget.get_gop_equipment_table()
            return res

    def auto_cancel_po(self):
        po = self.env['purchase.order'].search([
            ('state', 'in', ('purchase', 'done')),
            ('po', '=', True),
            ('po_expiry_date', '<', datetime.now()),
            ('invoice_ids', '=', False),
        ])

        # seharusnya write() tidak perlu looping
        # tapi karena di override dan tidak di handling error di line 1883 jika tidak dilooping
        # - Y -
        for purchase in po:
            if not purchase.is_services_orders or not purchase.is_subcontracting:
                purchase.write({'state': 'cancel'})

    def action_create_bill_2(self):
        pass

    @api.onchange('is_subcontracting')
    def _onchange_is_subcontracting(self):
        context = dict(self.env.context) or {}
        if context.get('services_good'):
            self.is_subcontracting = True

    # @api.onchange('is_material_orders')
    # def _onchange_is_material_orders(self):
    #     context = dict(self.env.context) or {}
    #     if context.get('goods_order'):
    #         self.is_material_orders = True

    @api.onchange('cost_sheet')
    def _onchange_cost_sheet(self):
        self.analytic_account_group_ids = False
        self.variable_line_ids = [(5, 0, 0)]
        if self.cost_sheet:
            cost_sheet = self.cost_sheet
            self.analytic_account_group_ids = cost_sheet.account_tag_ids.ids
        for rec in self.cost_sheet:
            for section in rec.material_subcon_ids:
                self.variable_line_ids = [(0, 0, {
                    'cs_subcon_id': section.id,
                    'project_scope': section.project_scope,
                    'section': section.section_name,
                    'variable': section.variable,
                    'uom': section.uom_id,
                    'budget_amount': section.price_unit,
                    'budget_amount_total': section.budgeted_amt_left
                })]

    variable_line_ids = fields.One2many('rfq.variable.line', 'variable_id', string='Variable Line')

    # Service Line Start
    service_line_ids = fields.One2many('rfq.service.line', 'service_id', string='Service Line')
    sl_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_sl_amount_all',
                                        tracking=True)
    sl_discount_amt = fields.Monetary(string='- Discount', store=True, readonly=True, compute='_sl_amount_all')
    sl_discount_amt_line = fields.Float(compute='_sl_amount_all', string='- Line Discount',
                                        digits_compute=dp.get_precision('Line Discount'), store=True, readonly=True)
    sl_amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_sl_amount_all')
    sl_amount_total = fields.Monetary(string='Total Service', store=True, readonly=True, compute='_sl_amount_all')

    discount_method_sl = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], 'Discount Method',
                                          default='fixed')
    discount_amount_sl = fields.Float('Discount Amount', default=0.0)

    @api.depends('service_line_ids.total')
    def _sl_amount_all(self):
        for order in self:
            sl_amount_untaxed = sl_amount_tax = 0.0
            for line in order.service_line_ids:
                line._compute_sl_amount()
                sl_amount_untaxed += line.subtotal
                sl_amount_tax += line.tax
            order.update({
                'sl_amount_untaxed': order.currency_id.round(sl_amount_untaxed),
                'sl_amount_tax': order.currency_id.round(sl_amount_tax),
                'sl_amount_total': sl_amount_untaxed + sl_amount_tax,
            })

    @api.onchange('discount_type', 'discount_method_ml', 'discount_amount_ml')
    def set_disc_ml(self):
        for res in self:
            if res.discount_type == 'global':
                for line in res.material_line_ids:
                    line.update({
                        'discount_method': res.discount_method_ml,
                        'discount_amount': res.discount_amount_ml
                    })

    # Service Line End

    # Material Line Start
    material_line_ids = fields.One2many('rfq.material.line', 'material_id', string='Material Line')
    ml_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_ml_amount_all',
                                        tracking=True)
    ml_discount_amt = fields.Monetary(string='- Discount', store=True, readonly=True, compute='_ml_amount_all')
    ml_discount_amt_line = fields.Float(compute='_ml_amount_all', string='- Line Discount',
                                        digits_compute=dp.get_precision('Line Discount'), store=True, readonly=True)
    ml_amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_ml_amount_all')
    ml_amount_total = fields.Monetary(string='Total Material', store=True, readonly=True, compute='_ml_amount_all')

    discount_method_ml = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], 'Discount Method',
                                          default='fixed')
    discount_amount_ml = fields.Float('Discount Amount', default=0.0)

    @api.depends('material_line_ids.total')
    def _ml_amount_all(self):
        for order in self:
            ml_amount_untaxed = ml_amount_tax = 0.0
            for line in order.material_line_ids:
                line._compute_ml_amount()
                ml_amount_untaxed += line.subtotal
                ml_amount_tax += line.tax
            order.update({
                'ml_amount_untaxed': order.currency_id.round(ml_amount_untaxed),
                'ml_amount_tax': order.currency_id.round(ml_amount_tax),
                'ml_amount_total': ml_amount_untaxed + ml_amount_tax,
            })

    @api.onchange('discount_type', 'discount_method_ml', 'discount_amount_ml')
    def set_disc_ml(self):
        for res in self:
            if res.discount_type == 'global':
                for line in res.material_line_ids:
                    line.update({
                        'discount_method': res.discount_method_ml,
                        'discount_amount': res.discount_amount_ml
                    })

    # Material Line End

    # Equipment Line Start  
    equipment_line_ids = fields.One2many('rfq.equipment.line', 'equipment_id', string='Equipment Line')
    el_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_el_amount_all',
                                        tracking=True)
    el_discount_amt = fields.Monetary(string='- Discount', store=True, readonly=True, compute='_el_amount_all')
    el_discount_amt_line = fields.Float(compute='_el_amount_all', string='- Line Discount',
                                        digits_compute=dp.get_precision('Line Discount'), store=True, readonly=True)
    el_amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_el_amount_all')
    el_amount_total = fields.Monetary(string='Total Equipment', store=True, readonly=True, compute='_el_amount_all')

    discount_method_el = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], 'Discount Method',
                                          default='fixed')
    discount_amount_el = fields.Float('Discount Amount', default=0.0)

    @api.depends('equipment_line_ids.total')
    def _el_amount_all(self):
        for order in self:
            el_amount_untaxed = el_amount_tax = 0.0
            for line in order.equipment_line_ids:
                line._compute_el_amount()
                el_amount_untaxed += line.subtotal
                el_amount_tax += line.tax
            order.update({
                'el_amount_untaxed': order.currency_id.round(el_amount_untaxed),
                'el_amount_tax': order.currency_id.round(el_amount_tax),
                'el_amount_total': el_amount_untaxed + el_amount_tax,
            })

    @api.onchange('discount_type', 'discount_method_el', 'discount_amount_el')
    def set_disc_el(self):
        for res in self:
            if res.discount_type == 'global':
                for line in res.equipment_line_ids:
                    line.update({
                        'discount_method': res.discount_method_el,
                        'discount_amount': res.discount_amount_el
                    })

    # Equipment Line End

    # Labour Line Start  
    labour_line_ids = fields.One2many('rfq.labour.line', 'labour_id', string='Labour Line')
    ll_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_ll_amount_all',
                                        tracking=True)
    ll_discount_amt = fields.Monetary(string='- Discount', store=True, readonly=True, compute='_ll_amount_all')
    ll_discount_amt_line = fields.Float(compute='_ll_amount_all', string='- Line Discount',
                                        digits_compute=dp.get_precision('Line Discount'), store=True, readonly=True)
    ll_amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_ll_amount_all')
    ll_amount_total = fields.Monetary(string='Total Labour', store=True, readonly=True, compute='_ll_amount_all')

    discount_method_ll = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], 'Discount Method',
                                          default='fixed')
    discount_amount_ll = fields.Float('Discount Amount', default=0.0)

    @api.depends('labour_line_ids.total')
    def _ll_amount_all(self):
        for order in self:
            ll_amount_untaxed = ll_amount_tax = 0.0
            for line in order.labour_line_ids:
                line._compute_ll_amount()
                ll_amount_untaxed += line.subtotal
                ll_amount_tax += line.tax
            order.update({
                'll_amount_untaxed': order.currency_id.round(ll_amount_untaxed),
                'll_amount_tax': order.currency_id.round(ll_amount_tax),
                'll_amount_total': ll_amount_untaxed + ll_amount_tax,
            })

    @api.onchange('discount_type', 'discount_method_ll', 'discount_amount_ll')
    def set_disc_ll(self):
        for res in self:
            if res.discount_type == 'global':
                for line in res.labour_line_ids:
                    line.update({
                        'discount_method': res.discount_method_ll,
                        'discount_amount': res.discount_amount_ll
                    })

    # Labour Line End

    # Overhead Line Start  
    overhead_line_ids = fields.One2many('rfq.overhead.line', 'overhead_id', string='Overhead Line')
    ol_amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_ol_amount_all',
                                        tracking=True)
    ol_discount_amt = fields.Monetary(string='- Discount', store=True, readonly=True, compute='_ol_amount_all')
    ol_discount_amt_line = fields.Float(compute='_ol_amount_all', string='- Line Discount',
                                        digits_compute=dp.get_precision('Line Discount'), store=True, readonly=True)
    ol_amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_ol_amount_all')
    ol_amount_total = fields.Monetary(string='Total Overhead', store=True, readonly=True, compute='_ol_amount_all')

    discount_method_ol = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], 'Discount Method',
                                          default='fixed')
    discount_amount_ol = fields.Float('Discount Amount', default=0.0)

    @api.depends('overhead_line_ids.total')
    def _ol_amount_all(self):
        for order in self:
            ol_amount_untaxed = ol_amount_tax = 0.0
            for line in order.overhead_line_ids:
                line._compute_ol_amount()
                ol_amount_untaxed += line.subtotal
                ol_amount_tax += line.tax
            order.update({
                'ol_amount_untaxed': order.currency_id.round(ol_amount_untaxed),
                'ol_amount_tax': order.currency_id.round(ol_amount_tax),
                'ol_amount_total': ol_amount_untaxed + ol_amount_tax,
            })

    @api.onchange('discount_type', 'discount_method_ol', 'discount_amount_ol')
    def set_disc_ol(self):
        for res in self:
            if res.discount_type == 'global':
                for line in res.overhead_line_ids:
                    line.update({
                        'discount_method': res.discount_method_ol,
                        'discount_amount': res.discount_amount_ol
                    })

    # Total All Start
    material_total = fields.Monetary(string='Material Total', store=True, readonly=True, compute='_get_material_total')
    service_total = fields.Monetary(string='Service Total', store=True, readonly=True, compute='_get_service_total')
    equipment_total = fields.Monetary(string='Equipment Total', store=True, readonly=True,
                                      compute='_get_equipment_total')
    labour_total = fields.Monetary(string='Labour Total', store=True, readonly=True, compute='_get_labour_total')
    overhead_total = fields.Monetary(string='Overhead Total', store=True, readonly=True, compute='_get_overhead_total')

    total = fields.Float(string='Total', store=True, readonly=True, compute='_compute_amount_cons')
    discount_amount = fields.Float(string='Discount (-)', store=True, readonly=True, compute='_compute_total')
    discounted_total = fields.Float(string='Contract Total', store=True, readonly=True, compute='_compute_total')
    tax_amount = fields.Float(string='Tax', store=True, readonly=True, compute='_compute_amount_cons')
    total_all_estimation = fields.Float(string='Total', store=True, readonly=True, compute='_compute_total_estimation')
    total_all = fields.Float(string='Total', store=True, readonly=True, compute='_compute_total')

    @api.depends('discount_amount_global', 'variable_line_ids', 'tax_id')
    def _compute_amount_cons(self):
        # self.total = 0
        self.tax_amount = 0
        total = 0
        self.onchange_subcon_estimations()
        for record in self:
            if record.variable_line_ids:
                for line in record.variable_line_ids:
                    variable_price = (line.quantity * line.sub_total)
                    total += variable_price
                record.total = total
            else:
                record.total = 0
        self._compute_total()

    def _compute_total(self):
        self.discounted_total = 0
        self.discount_amount = 0
        self.total_all = 0
        for res in self:
            if res.is_subcontracting == True:
                if res.discount_type == 'global':
                    if res.discount_method_global == 'fix':
                        res.discount_amount = res.discount_amount_global
                    elif res.discount_method_global == 'per':
                        res.discount_amount = res.total * (res.discount_amount_global / 100)
                elif res.discount_type == 'line':
                    for variable_line in res.variable_line_ids:
                        if variable_line.discount_method == 'fixed':
                            res.discount_amount += variable_line.discount_amount
                        elif variable_line.discount_method == 'percentage':
                            res.discount_amount += variable_line.total * (variable_line.discount_amount / 100)
                discounted = (res.total - res.discount_amount)

                line_tax_id_amount1 = 0
                for tax_line in res.tax_id:
                    line_tax_id_amount1 += tax_line.amount
                total_tax = discounted * (line_tax_id_amount1 / 100)

                total_all = (discounted + total_tax)
                self.write({'discounted_total': discounted,
                            'tax_amount': total_tax,
                            'total_all': total_all,
                            })
            else:
                total_all = res.amount_total
                self.write({
                    'total_all': total_all
                })
            if res.budgeting_method == 'gop_budget':
                res._get_gop_budget_line()

    @api.onchange('order_line')
    def _get_gop_budget_line(self):
        self.gop_budget_ids = [(5, 0, 0)]
        if self.project:
            if self.budgeting_method == 'gop_budget':
                gop_budget_dict = {}
                for item in self.order_line:
                    # key_gop_budget = project_scope + section_name + group_of_product
                    key_gop_budget = str(item.type) + str(item.project_scope.id) + str(item.section.id) + str(item.group_of_product.id)
                    if gop_budget_dict.get(key_gop_budget, False):
                        gop_budget_dict[key_gop_budget]['gop_amount_total'] += item.price_subtotal
                    else:
                        gop_budget_dict[key_gop_budget] = {
                            'type': item.type,
                            'project_scope': item.project_scope.id,
                            'section_name': item.section.id,
                            'group_of_product': item.group_of_product.id,
                            'gop_amount_total': item.price_subtotal,
                        }

                self.gop_budget_ids = [(0, 0, item) for k, item in gop_budget_dict.items()]
                for gop in self.gop_budget_ids:
                    gop._onchange_product()

    @api.depends('ml_amount_total')
    def _get_material_total(self):
        for order in self:
            order.update({
                'material_total': order.ml_amount_total,
                'service_total': order.sl_amount_total,
                'equipment_total': order.el_amount_total,
                'labour_total': order.ll_amount_total,
                'overhead_total': order.ol_amount_total,
            })

    @api.depends('sl_amount_total')
    def _get_service_total(self):
        for order in self:
            order.update({
                'material_total': order.ml_amount_total,
                'service_total': order.sl_amount_total,
                'equipment_total': order.el_amount_total,
                'labour_total': order.ll_amount_total,
                'overhead_total': order.ol_amount_total,
            })

    @api.depends('el_amount_total')
    def _get_equipment_total(self):
        for order in self:
            order.update({
                'material_total': order.ml_amount_total,
                'service_total': order.sl_amount_total,
                'equipment_total': order.el_amount_total,
                'labour_total': order.ll_amount_total,
                'overhead_total': order.ol_amount_total,
            })

    @api.depends('ll_amount_total')
    def _get_labour_total(self):
        for order in self:
            order.update({
                'material_total': order.ml_amount_total,
                'service_total': order.sl_amount_total,
                'equipment_total': order.el_amount_total,
                'labour_total': order.ll_amount_total,
                'overhead_total': order.ol_amount_total,
            })

    @api.depends('ol_amount_total')
    def _get_overhead_total(self):
        for order in self:
            order.update({
                'material_total': order.ml_amount_total,
                'service_total': order.sl_amount_total,
                'equipment_total': order.el_amount_total,
                'labour_total': order.ll_amount_total,
                'overhead_total': order.ol_amount_total,
            })

    # @api.depends('material_total','service_total','equipment_total','labour_total','overhead_total')
    # def _get_total_all(self):
    #     for order in self:
    #         order.update({
    #             'total_all': order.material_total + order.service_total + order.equipment_total + order.labour_total + order.overhead_total,
    #         })

    @api.depends('split_material', 'material_total', 'service_total', 'equipment_total', 'labour_total',
                 'overhead_total')
    def _compute_total_estimation(self):
        for res in self:
            if res.split_material == True:
                res.total_all_estimation = res.service_total + res.equipment_total + res.labour_total + res.overhead_total
            else:
                res.total_all_estimation = res.material_total + res.service_total + res.equipment_total + res.labour_total + res.overhead_total

    all_total = fields.Monetary('Total', compute='_compute_all_total')

    @api.depends('all_total')
    def _compute_all_total(self):
        for record in self:
            record.all_total = record.ml_amount_total + record.sl_amount_total + record.el_amount_total + record.ll_amount_total + record.ol_amount_total + record.total_all

    @api.onchange('material_line_ids', 'labour_line_ids', 'service_line_ids', 'overhead_line_ids', 'equipment_line_ids', 'variable_line_ids')
    def onchange_subcon_estimations(self):
        for record in self:
            if record.is_subcontracting:
                for subcon in record.variable_line_ids:
                    subcon_total = 0
                    for material in record.material_line_ids.filtered(lambda x: x.variable._origin.id == subcon.variable._origin.id and x.section._origin.id == subcon.section._origin.id and x.project_scope._origin.id == subcon.project_scope._origin.id):
                        subcon_total += material.subtotal
                    for labour in record.labour_line_ids.filtered(lambda x: x.variable._origin.id == subcon.variable._origin.id and x.section._origin.id == subcon.section._origin.id and x.project_scope._origin.id == subcon.project_scope._origin.id):
                        subcon_total += labour.subtotal
                    for service in record.service_line_ids.filtered(lambda x: x.variable._origin.id == subcon.variable._origin.id and x.section._origin.id == subcon.section._origin.id and x.project_scope._origin.id == subcon.project_scope._origin.id):
                        subcon_total += service.subtotal
                    for overhead in record.overhead_line_ids.filtered(lambda x: x.variable._origin.id == subcon.variable._origin.id and x.section._origin.id == subcon.section._origin.id and x.project_scope._origin.id == subcon.project_scope._origin.id):
                        subcon_total += overhead.subtotal
                    for equipment in record.equipment_line_ids.filtered(lambda x: x.variable._origin.id == subcon.variable._origin.id and x.section._origin.id == subcon.section._origin.id and x.project_scope._origin.id == subcon.project_scope._origin.id):
                        subcon_total += equipment.subtotal
                    subcon.total = subcon_total
                    subcon.sub_total = subcon_total/subcon.quantity

                # if not is_compute:
                #     record._compute_amount_cons()


class RFQVariableLine(models.Model):
    _name = 'rfq.variable.line'
    _description = "Variable Line Request for Quotations"
    _order = "sequence"

    name = fields.Char('name', compute='_compute_name_po_line')
    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    cs_subcon_id = fields.Many2one('material.subcon', string='CS Subcon ID')
    bd_subcon_id = fields.Many2one('budget.subcon', string='BD Subcon ID')
    bd_subcon_ids = fields.Many2many('budget.gop.overhead', string='BD Subcon IDS')
    purchase_agreement = fields.Many2one('purchase.agreement', 'Purchase Agreement')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope', required=True, )
    section = fields.Many2one('section.line', 'Section', required=True)
    variable_id = fields.Many2one('purchase.order', 'Variable ID')
    variable_ref = fields.Many2one('variable.template', 'Variable')
    variable = fields.Many2one('variable.template', 'Job Subcon', required=True)
    quantity = fields.Float('Quantity', default="1")
    budget_quantity = fields.Float('Budget Quantity')
    uom = fields.Many2one('uom.uom', string='UoM', readonly=True)
    sub_total = fields.Float('Unit Price')
    tax_id = fields.Many2many(related='variable_id.tax_id', string='Taxes')
    tax_amount = fields.Float(string='Taxes Amount', compute='onchange_tax_amount')
    discount_method = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Discount Method")
    discount_amount = fields.Float('Discount Amount')
    budget_amount = fields.Float('Budget Unit Price', compute='_onchange_split_material')
    total = fields.Float('Total')
    budget_amount_total = fields.Float('Budget Amount', compute='_onchange_split_material')
    is_reserved = fields.Boolean('Reserved', default=False)
    progressive_claim_perc = fields.Float(string="Progressive Claim (%)")
    duration = fields.Integer('Duration', related='variable_id.duration', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('billed', 'Billed'),
        ('rejected', 'Rejected'),
        ('done', 'done'),
        ('canceled', 'Canceled'),
    ], string='Purchase Status', default='draft')
    project = fields.Many2one(related='variable_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    dp_amount_percentage = fields.Float(string="Line Percentage (%)", compute='_compute_dp_amount')
    dp_amount = fields.Float(string="DP Amount")
    retention_amount_percentage = fields.Float(string="Retention Amount (%)", compute='_compute_retention_amount')
    retention_amount = fields.Float(string="Retention Amount")
    retention_2_amount_percentage = fields.Float(string="Retention 2 Amount (%)", compute='_compute_retention_amount')
    retention_2_amount = fields.Float(string="Retention 2 Amount")
    is_subtotal_readonly = fields.Boolean(string="Subtotal Readonly")
    
    @api.depends('project_scope','section','variable')
    def _compute_name_po_line(self):
        for rec in self:
            scope = rec.project_scope.name
            section = rec.section.name
            subcon = rec.variable.name
            if rec.project_scope and rec.section and rec.variable:
                record = 'PO (Subcon) - ' + scope + ' - ' + section + ' - ' + subcon
            else:
                record = 'PO (Subcon)'
            rec.write({'name': record})

    @api.onchange('variable_id.is_multiple_budget',  'project_scope', 'section', 'variable')
    def _onchange_subcon(self):
        for line in self:
            if line.project_scope and line.section and line.variable:
                line.cs_subcon_id = False
                line.bd_subcon_id = False
                line.bd_subcon_ids = False
                line.cs_subcon_id = self.env['material.subcon'].search([('job_sheet_id', '=', line.variable_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('variable', '=', line.variable.id)])
                
                if line.variable_id.is_multiple_budget == False:
                    if line.variable_id.project_budget:
                        line.bd_subcon_id = self.env['budget.subcon'].search([('budget_id', '=', line.variable_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('subcon_id', '=', line.variable.id)])

                else:
                    budget_ids = []
                    budget = self.env['budget.subcon'].search([('budget_id', 'in', line.variable_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('subcon_id', '=', line.variable.id)])
                    if budget:
                        for bud in budget:
                            budget_ids.append((0,0, bud.id))
                
                    line.bd_subcon_ids = budget_ids

    @api.depends('variable_id')
    def _compute_dp_amount(self):
        for rec in self:
            if rec.variable_id.total != 0:
                po_dp_amount = 0
                if rec.variable_id.down_payment_method == 'per':
                    po_dp_amount = (rec.variable_id.down_payment * rec.variable_id.total)/100
                elif rec.variable_id.down_payment_method == 'fix':
                    po_dp_amount = rec.down_payment
                rec.dp_amount_percentage = (rec.total / rec.variable_id.total)
                rec.dp_amount = po_dp_amount * rec.dp_amount_percentage
            else:
                rec.dp_amount_percentage = 0
                rec.dp_amount = 0

    @api.depends('variable_id')
    def _compute_retention_amount(self):
        for rec in self:
            if rec.variable_id.total != 0:
                po_retention_amount = (rec.variable_id.retention_1 * rec.variable_id.total)/100
                rec.retention_amount_percentage = (rec.total / rec.variable_id.total)
                rec.retention_amount = po_retention_amount * rec.retention_amount_percentage

                po_retention_2_amount = (rec.variable_id.retention_2 * rec.variable_id.total)/100
                rec.retention_2_amount_percentage = (rec.total / rec.variable_id.total)
                rec.retention_2_amount = po_retention_2_amount * rec.retention_2_amount_percentage
            else:
                rec.retention_amount_percentage = 0
                rec.retention_amount = 0

                rec.retention_2_amount_percentage = 0
                rec.retention_2_amount = 0

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('variable_id.split_material', 'budget_amount', 'budget_amount_total')
    def _onchange_split_material(self):
        for rec in self:
            if rec.variable_id.project_budget:
                if rec.variable_id.split_material == True:
                    rec.budget_amount = rec.bd_subcon_id.amount - rec.variable.total_variable_material
                    rec.budget_amount_total = rec.budget_amount * rec.quantity
                else:
                    rec.budget_amount = rec.bd_subcon_id.amount
                    rec.budget_amount_total = rec.budget_amount * rec.quantity
            else:
                if rec.variable_id.split_material == True:
                    rec.budget_amount = rec.cs_subcon_id.price_unit - rec.variable.total_variable_material
                    rec.budget_amount_total = rec.budget_amount * rec.quantity
                else:
                    rec.budget_amount = rec.cs_subcon_id.price_unit
                    rec.budget_amount_total = rec.budget_amount * rec.quantity

    @api.onchange('variable')
    def onchange_variable(self):
        res = {}
        if not self.variable:
            return res
        self.uom = self.variable.variable_uom.id
        self.quantity = 1.0
        self.sub_total = self.variable.total_variable

    # @api.onchange('quantity', 'sub_total')
    # def onchange_total(self):
    #     price = 0.0
    #     for line in self:
    #         price = (line.quantity * line.sub_total)
    #         line.total = price

    @api.depends('total', 'tax_id')
    def onchange_tax_amount(self):
        for line in self:
            line_tax_id_amount = 0
            for tax_line in line.tax_id:
                line_tax_id_amount += tax_line.amount
            line.tax_amount = line.total * (line_tax_id_amount / 100)
            return line_tax_id_amount

    @api.depends('variable_id.variable_line_ids', 'variable_id.variable_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.variable_id.variable_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('rfq_variable_line') or ('New')
        res = super(RFQVariableLine, self).create(vals)
        return res


class RFQMaterialLine(models.Model):
    _name = 'rfq.material.line'
    _description = "Material Line Request for Quotations"
    _order = "sequence"

    @api.model
    def _default_domain_ml(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            return [('type', 'in', ('consu', 'product'))]
        elif context.get('services_good'):
            return [('type', '=', 'service')]

    sequence = fields.Integer('Sequence', default=1)
    material_id = fields.Many2one('purchase.order', 'Material ID')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    product = fields.Many2one('product.product', 'Product')
    description = fields.Text(string='Description')
    purchase_tender = fields.Many2one('purchase.agreement', 'Purchase Tender')
    receipt_date = fields.Datetime('Receipt Date')
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    discount_method = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Discount Method")
    discount_amount = fields.Float('Discount Amount')
    note_comment = fields.Char('Note/Comment')
    quantity = fields.Float('Quantity')
    budget_quantity = fields.Float('Budget Quantity')
    uom = fields.Many2one('uom.uom', 'Unit of Measure')
    secondary_quantity = fields.Float('Secondary Qty')
    secondary_uom = fields.Many2one('uom.uom', 'Secondary UOM')
    unit_price = fields.Float('Unit Price')
    budget_unit_price = fields.Float('Budget Unit Price')
    taxes = fields.Many2many(related='material_id.tax_id', string='Taxes')
    lpp = fields.Float('Last Purchased Price')
    lpp_of_vendor = fields.Float('Last Purchased Price of Vendor')
    remining_budget_amount = fields.Float('Budget Amount Left')
    subtotal = fields.Monetary(compute='_compute_ml_amount', string='Subtotal', store=True)
    total = fields.Monetary(compute='_compute_ml_amount', string='Total', store=True)
    tax = fields.Float(compute='_compute_ml_amount', string='Tax', store=True)
    partner_id = fields.Many2one('res.partner', related='material_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='material_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='material_id.date_order', string='Order Date', readonly=True)
    discount_amt = fields.Float('Discount Final Amount')
    discount_type = fields.Selection(related='material_id.discount_type', string="Discount Applies to")
    company_id = fields.Many2one('res.company', related='material_id.company_id', string='Company', store=True,
                                 readonly=True)
    project = fields.Many2one(related='material_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product_ml(self):
        res = {}
        if not self.product:
            return res
        self.receipt_date = datetime.today()
        product_lang = self.product.with_context(lang=get_lang(self.env).code)
        self.description = self._get_rfq_material_description(product_lang)
        self.quantity = 1.0
        self.uom = self.product.uom_id.id
        self.unit_price = self.product.standard_price
        self.taxes = self.product.taxes_id
        self.lpp = self.product.last_purchase_price

    def _get_rfq_material_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    @api.depends('quantity', 'unit_price', 'taxes')
    def _compute_ml_amount(self):
        for line in self:
            vals = line.ml_prepare_compute_all_values()
            taxes = line.taxes.compute_all(
                vals['unit_price'],
                vals['currency_id'],
                vals['quantity'],
                vals['product'],
                vals['partner'])
            line.update({
                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
            })

    def ml_prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'unit_price': self.unit_price,
            'currency_id': self.material_id.currency_id,
            'quantity': self.quantity,
            'product': self.product,
            'partner': self.material_id.partner_id,
        }


class RFQServiceLine(models.Model):
    _name = 'rfq.service.line'
    _description = "Service Line Request for Quotations"
    _order = "sequence"

    @api.model
    def _default_domain_sl(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            return [('type', 'in', ('consu', 'product'))]
        elif context.get('services_good'):
            return [('type', '=', 'service')]

    sequence = fields.Integer('Sequence', default=1)
    service_id = fields.Many2one('purchase.order', 'Service ID')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    product = fields.Many2one('product.product', 'Product')
    description = fields.Text(string='Description')
    purchase_tender = fields.Many2one('purchase.agreement', 'Purchase Tender')
    receipt_date = fields.Datetime('Receipt Date')
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    discount_method = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Discount Method")
    discount_amount = fields.Float('Discount Amount')
    note_comment = fields.Char('Note/Comment')
    quantity = fields.Float('Quantity')
    budget_quantity = fields.Float('Budget Quantity')
    uom = fields.Many2one('uom.uom', 'Unit of Measure')
    secondary_quantity = fields.Float('Secondary Qty')
    secondary_uom = fields.Many2one('uom.uom', 'Secondary UOM')
    unit_price = fields.Float('Unit Price')
    budget_unit_price = fields.Float('Budget Unit Price')
    taxes = fields.Many2many(related='service_id.tax_id', string='Taxes')
    lpp = fields.Float('Last Purchased Price')
    lpp_of_vendor = fields.Float('Last Purchased Price of Vendor')
    remining_budget_amount = fields.Float('Budget Amount Left')
    subtotal = fields.Monetary(compute='_compute_sl_amount', string='Subtotal', store=True)
    total = fields.Monetary(compute='_compute_sl_amount', string='Total', store=True)
    tax = fields.Float(compute='_compute_sl_amount', string='Tax', store=True)
    partner_id = fields.Many2one('res.partner', related='service_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='service_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='service_id.date_order', string='Order Date', readonly=True)
    discount_amt = fields.Float('Discount Final Amount')
    discount_type = fields.Selection(related='service_id.discount_type', string="Discount Applies to")
    company_id = fields.Many2one('res.company', related='service_id.company_id', string='Company', store=True,
                                 readonly=True)
    project = fields.Many2one(related='service_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product_sl(self):
        res = {}
        if not self.product:
            return res
        self.receipt_date = datetime.today()
        product_lang = self.product.with_context(lang=get_lang(self.env).code)
        self.description = self._get_rfq_service_description(product_lang)
        self.quantity = 1.0
        self.uom = self.product.uom_id.id
        self.unit_price = self.product.standard_price
        self.taxes = self.product.taxes_id
        self.lpp = self.product.last_purchase_price

    def _get_rfq_service_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    @api.depends('quantity', 'unit_price', 'taxes')
    def _compute_sl_amount(self):
        for line in self:
            vals = line.sl_prepare_compute_all_values()
            taxes = line.taxes.compute_all(
                vals['unit_price'],
                vals['currency_id'],
                vals['quantity'],
                vals['product'],
                vals['partner'])
            line.update({
                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
            })

    def sl_prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'unit_price': self.unit_price,
            'currency_id': self.service_id.currency_id,
            'quantity': self.quantity,
            'product': self.product,
            'partner': self.service_id.partner_id,
        }


class RFQEquipmentLine(models.Model):
    _name = 'rfq.equipment.line'
    _description = "Equipment Line Request for Quotations"
    _order = "sequence"

    @api.model
    def _default_domain_el(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            return [('type', 'in', ('consu', 'product'))]
        elif context.get('equipments_good'):
            return [('type', '=', 'equipment')]

    sequence = fields.Integer('Sequence', default=1)
    equipment_id = fields.Many2one('purchase.order', 'Equipment ID')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    product = fields.Many2one('product.product', 'Product')
    description = fields.Text(string='Description')
    purchase_tender = fields.Many2one('purchase.agreement', 'Purchase Tender')
    receipt_date = fields.Datetime('Receipt Date')
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    discount_method = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Discount Method")
    discount_amount = fields.Float('Discount Amount')
    note_comment = fields.Char('Note/Comment')
    quantity = fields.Float('Quantity')
    budget_quantity = fields.Float('Budget Quantity')
    uom = fields.Many2one('uom.uom', 'Unit of Measure')
    secondary_quantity = fields.Float('Secondary Qty')
    secondary_uom = fields.Many2one('uom.uom', 'Secondary UOM')
    unit_price = fields.Float('Unit Price')
    budget_unit_price = fields.Float('Budget Unit Price')
    taxes = fields.Many2many(related='equipment_id.tax_id', string='Taxes')
    lpp = fields.Float('Last Purchased Price')
    lpp_of_vendor = fields.Float('Last Purchased Price of Vendor')
    remining_budget_amount = fields.Float('Budget Amount Left')
    subtotal = fields.Monetary(compute='_compute_el_amount', string='Subtotal', store=True)
    total = fields.Monetary(compute='_compute_el_amount', string='Total', store=True)
    tax = fields.Float(compute='_compute_el_amount', string='Tax', store=True)
    partner_id = fields.Many2one('res.partner', related='equipment_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='equipment_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='equipment_id.date_order', string='Order Date', readonly=True)
    discount_amt = fields.Float('Discount Final Amount')
    discount_type = fields.Selection(related='equipment_id.discount_type', string="Discount Applies to")
    company_id = fields.Many2one('res.company', related='equipment_id.company_id', string='Company', store=True,
                                 readonly=True)
    project = fields.Many2one(related='equipment_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product_el(self):
        res = {}
        if not self.product:
            return res
        self.receipt_date = datetime.today()
        product_lang = self.product.with_context(lang=get_lang(self.env).code)
        self.description = self._get_rfq_equipment_description(product_lang)
        self.quantity = 1.0
        self.uom = self.product.uom_id.id
        self.unit_price = self.product.standard_price
        self.taxes = self.product.taxes_id
        self.lpp = self.product.last_purchase_price

    def _get_rfq_equipment_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    @api.depends('quantity', 'unit_price', 'taxes')
    def _compute_el_amount(self):
        for line in self:
            vals = line.el_prepare_compute_all_values()
            taxes = line.taxes.compute_all(
                vals['unit_price'],
                vals['currency_id'],
                vals['quantity'],
                vals['product'],
                vals['partner'])
            line.update({
                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
            })

    def el_prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'unit_price': self.unit_price,
            'currency_id': self.equipment_id.currency_id,
            'quantity': self.quantity,
            'product': self.product,
            'partner': self.equipment_id.partner_id,
        }


class RFQLabourLine(models.Model):
    _name = 'rfq.labour.line'
    _description = "Labour Line Request for Quotations"
    _order = "sequence"

    @api.model
    def _default_domain_ll(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            return [('type', 'in', ('consu', 'product'))]
        elif context.get('labours_good'):
            return [('type', '=', 'labour')]

    sequence = fields.Integer('Sequence', default=1)
    labour_id = fields.Many2one('purchase.order', 'Labour ID')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    product = fields.Many2one('product.product', 'Product')
    description = fields.Text(string='Description')
    purchase_tender = fields.Many2one('purchase.agreement', 'Purchase Tender')
    receipt_date = fields.Datetime('Receipt Date')
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    discount_method = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Discount Method")
    discount_amount = fields.Float('Discount Amount')
    note_comment = fields.Char('Note/Comment')
    quantity = fields.Float('Quantity')
    budget_quantity = fields.Float('Budget Quantity')
    uom = fields.Many2one('uom.uom', 'Unit of Measure')
    secondary_quantity = fields.Float('Secondary Qty')
    secondary_uom = fields.Many2one('uom.uom', 'Secondary UOM')
    unit_price = fields.Float('Unit Price')
    budget_unit_price = fields.Float('Budget Unit Price')
    taxes = fields.Many2many(related='labour_id.tax_id', string='Taxes')
    lpp = fields.Float('Last Purchased Price')
    lpp_of_vendor = fields.Float('Last Purchased Price of Vendor')
    remining_budget_amount = fields.Float('Budget Amount Left')
    subtotal = fields.Monetary(compute='_compute_ll_amount', string='Subtotal', store=True)
    total = fields.Monetary(compute='_compute_ll_amount', string='Total', store=True)
    tax = fields.Float(compute='_compute_ll_amount', string='Tax', store=True)
    partner_id = fields.Many2one('res.partner', related='labour_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='labour_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='labour_id.date_order', string='Order Date', readonly=True)
    discount_amt = fields.Float('Discount Final Amount')
    discount_type = fields.Selection(related='labour_id.discount_type', string="Discount Applies to")
    company_id = fields.Many2one('res.company', related='labour_id.company_id', string='Company', store=True,
                                 readonly=True)
    project = fields.Many2one(related='labour_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
        
    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product_ll(self):
        res = {}
        if not self.product:
            return res
        self.receipt_date = datetime.today()
        product_lang = self.product.with_context(lang=get_lang(self.env).code)
        self.description = self._get_rfq_labour_description(product_lang)
        self.quantity = 1.0
        self.uom = self.product.uom_id.id
        self.unit_price = self.product.standard_price
        self.taxes = self.product.taxes_id
        self.lpp = self.product.last_purchase_price

    def _get_rfq_labour_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    @api.depends('quantity', 'unit_price', 'taxes')
    def _compute_ll_amount(self):
        for line in self:
            vals = line.ll_prepare_compute_all_values()
            taxes = line.taxes.compute_all(
                vals['unit_price'],
                vals['currency_id'],
                vals['quantity'],
                vals['product'],
                vals['partner'])
            line.update({
                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
            })

    def ll_prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'unit_price': self.unit_price,
            'currency_id': self.labour_id.currency_id,
            'quantity': self.quantity,
            'product': self.product,
            'partner': self.labour_id.partner_id,
        }


class RFQOverheadLine(models.Model):
    _name = 'rfq.overhead.line'
    _description = "Overhead Line Request for Quotations"
    _order = "sequence"

    @api.model
    def _default_domain_ol(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            return [('type', 'in', ('consu', 'product'))]
        elif context.get('services_good'):
            return [('type', '=', 'service')]

    sequence = fields.Integer('Sequence', default=1)
    overhead_id = fields.Many2one('purchase.order', 'Overhead ID')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    product = fields.Many2one('product.product', 'Product')
    description = fields.Text(string='Description')
    purchase_tender = fields.Many2one('purchase.agreement', 'Purchase Tender')
    receipt_date = fields.Datetime('Receipt Date')
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    discount_method = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Discount Method")
    discount_amount = fields.Float('Discount Amount')
    note_comment = fields.Char('Note/Comment')
    quantity = fields.Float('Quantity')
    budget_quantity = fields.Float('Budget Quantity')
    uom = fields.Many2one('uom.uom', 'Unit of Measure')
    secondary_quantity = fields.Float('Secondary Qty')
    secondary_uom = fields.Many2one('uom.uom', 'Secondary UOM')
    unit_price = fields.Float('Unit Price')
    budget_unit_price = fields.Float('Budget Unit Price')
    taxes = fields.Many2many(related='overhead_id.tax_id', string='Taxes')
    lpp = fields.Float('Last Purchased Price')
    lpp_of_vendor = fields.Float('Last Purchased Price of Vendor')
    remining_budget_amount = fields.Float('Budget Amount Left')
    subtotal = fields.Monetary(compute='_compute_ol_amount', string='Subtotal', store=True)
    total = fields.Monetary(compute='_compute_ol_amount', string='Total', store=True)
    tax = fields.Float(compute='_compute_ol_amount', string='Tax', store=True)
    partner_id = fields.Many2one('res.partner', related='overhead_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='overhead_id.currency_id', store=True, string='Currency', readonly=True)
    date_order = fields.Datetime(related='overhead_id.date_order', string='Order Date', readonly=True)
    discount_amt = fields.Float('Discount Final Amount')
    discount_type = fields.Selection(related='overhead_id.discount_type', string="Discount Applies to")
    company_id = fields.Many2one('res.company', related='overhead_id.company_id', string='Company', store=True,
                                 readonly=True)
    project = fields.Many2one(related='overhead_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product_ol(self):
        res = {}
        if not self.product:
            return res
        self.receipt_date = datetime.today()
        product_lang = self.product.with_context(lang=get_lang(self.env).code)
        self.description = self._get_rfq_overhead_description(product_lang)
        self.quantity = 1.0
        self.uom = self.product.uom_id.id
        self.unit_price = self.product.standard_price
        self.taxes = self.product.taxes_id
        self.lpp = self.product.last_purchase_price

    def _get_rfq_overhead_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    @api.depends('quantity', 'unit_price', 'taxes')
    def _compute_ol_amount(self):
        for line in self:
            vals = line.ol_prepare_compute_all_values()
            taxes = line.taxes.compute_all(
                vals['unit_price'],
                vals['currency_id'],
                vals['quantity'],
                vals['product'],
                vals['partner'])
            line.update({
                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
            })

    def ol_prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'unit_price': self.unit_price,
            'currency_id': self.overhead_id.currency_id,
            'quantity': self.quantity,
            'product': self.product,
            'partner': self.overhead_id.partner_id,
        }


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def check_uom(self, line, table_line):
        if table_line.uom_id.category_id.name == 'Working Time':
            if table_line.uom_id.name == 'Days' and line.product_uom.name == 'Hours':
                return [True, 'days']
            elif table_line.uom_id.name == 'Hours' and line.product_uom.name == 'Days':
                return [True, 'hours']
        return [False, False]

    def convert_to_days(self, line, table_line):
        if table_line.project_id.working_hour_hours:
            return line.quantity_done / table_line.project_id.working_hour_hours
        return

    def convert_to_hours(self, line, table_line):
        if table_line.project_id.working_hour_hours:
            return line.quantity_done * table_line.project_id.working_hour_hours
        return

    def update_received_material_cs(self, line, po_line):
        for cs in po_line.cs_material_id:
            working_time_uom_check = self.check_uom(line,cs)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, cs)
                else:
                    quantity_done = self.convert_to_hours(line, cs)
            else:
                quantity_done = line.quantity_done
            reserved = (cs.received_qty + quantity_done)
            for cos in po_line.order_id.cost_sheet:
                cos.material_ids = [(1, po_line.cs_material_id.id, {
                    'received_qty': reserved,
                })]
        return po_line

    def update_received_material_bd(self, line, po_line):
        for sub in po_line.bd_material_id:
            working_time_uom_check = self.check_uom(line, sub)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, sub)
                else:
                    quantity_done = self.convert_to_hours(line, sub)
            else:
                quantity_done = line.quantity_done
            reserved = (sub.qty_received + quantity_done)
            for bud in po_line.order_id.project_budget:
                bud.budget_material_ids = [(1, po_line.bd_material_id.id, {
                    'qty_received': reserved,
                })]
        return po_line

    def update_received_labour_cs(self, line, po_line):
        for cs in po_line.cs_labour_id:
            working_time_uom_check = self.check_uom(line,cs)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, cs)
                else:
                    quantity_done = self.convert_to_hours(line, cs)
            else:
                quantity_done = line.quantity_done
            reserved = (cs.received_qty + quantity_done)
            for cos in po_line.order_id.cost_sheet:
                cos.material_labour_ids = [(1, po_line.cs_labour_id.id, {
                    'received_qty': reserved,
                })]
        return po_line

    def update_received_labour_bd(self, line, po_line):
        for sub in po_line.bd_labour_id:
            working_time_uom_check = self.check_uom(line, sub)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, sub)
                else:
                    quantity_done = self.convert_to_hours(line, sub)
            else:
                quantity_done = line.quantity_done
            reserved = (sub.qty_received + quantity_done)
            for bud in po_line.order_id.project_budget:
                bud.budget_labour_ids = [(1, po_line.bd_labour_id.id, {
                    'qty_received': reserved,
                })]
        return po_line

    def update_received_overhead_cs(self, line, po_line):
        for cs in po_line.cs_overhead_id:
            working_time_uom_check = self.check_uom(line,cs)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, cs)
                else:
                    quantity_done = self.convert_to_hours(line, cs)
            else:
                quantity_done = line.quantity_done
            reserved = (cs.received_qty + quantity_done)
            for cos in po_line.order_id.cost_sheet:
                cos.material_overhead_ids = [(1, po_line.cs_overhead_id.id, {
                    'received_qty': reserved,
                })]
        return po_line

    def update_received_overhead_bd(self, line, po_line):
        for sub in po_line.bd_overhead_id:
            working_time_uom_check = self.check_uom(line, sub)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, sub)
                else:
                    quantity_done = self.convert_to_hours(line, sub)
            else:
                quantity_done = line.quantity_done
            reserved = (sub.qty_received + quantity_done)
            for bud in po_line.order_id.project_budget:
                bud.budget_overhead_ids = [(1, po_line.bd_overhead_id.id, {
                    'qty_received': reserved,
                })]
        return po_line

    def update_received_equipment_cs(self, line, po_line):
        for cs in po_line.cs_equipment_id:
            working_time_uom_check = self.check_uom(line,cs)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, cs)
                else:
                    quantity_done = self.convert_to_hours(line, cs)
            else:
                quantity_done = line.quantity_done
            for cos in po_line.order_id.cost_sheet:
                if line.picking_id.picking_type_id.code == 'outgoing':
                    increase = (cs.returned_qty + quantity_done)
                    decrease = (cs.received_qty - quantity_done)
                    act_qty = (cs.actual_used_qty + quantity_done)
                    amt_qty = (cs.actual_used_amt + (quantity_done * line.product_id.standard_price))
                    cos.material_equipment_ids = [(1, po_line.cs_equipment_id.id, {
                        'returned_qty': increase,
                        'received_qty': decrease,
                        'actual_used_qty': act_qty,
                        'actual_used_amt': amt_qty,
                    })]
                elif line.picking_id.picking_type_id.code == 'incoming':
                    reserved = (cs.received_qty + quantity_done)
                    cos.material_equipment_ids = [(1, po_line.cs_equipment_id.id, {
                        'received_qty': reserved,
                    })]
        return po_line

    def update_received_equipment_bd(self, line, po_line):
        for sub in po_line.bd_equipment_id:
            working_time_uom_check = self.check_uom(line, sub)
            if working_time_uom_check[0]:
                if working_time_uom_check[1] == 'days':
                    quantity_done = self.convert_to_days(line, sub)
                else:
                    quantity_done = self.convert_to_hours(line, sub)
            else:
                quantity_done = line.quantity_done
            for bud in po_line.order_id.project_budget:
                if line.picking_id.picking_type_id.code == 'outgoing':
                    increase = (sub.qty_returned + quantity_done)
                    decrease = (sub.qty_received - quantity_done)
                    act_qty = (sub.qty_used + quantity_done)
                    amt_qty = (sub.amt_used + (quantity_done * line.product_id.standard_price))
                    bud.budget_equipment_ids = [(1, po_line.bd_equipment_id.id, {
                        'qty_returned': increase,
                        'qty_received': decrease,
                        'qty_used': act_qty,
                        'amt_used': amt_qty,
                    })]
                elif line.picking_id.picking_type_id.code == 'incoming':
                    reserved = (sub.qty_received + quantity_done)
                    bud.budget_equipment_ids = [(1, po_line.bd_equipment_id.id, {
                        'qty_received': reserved,
                    })]
        return po_line

    def _action_done(self):
        res = super(StockPickingInherit, self)._action_done()
        for line in self.move_ids_without_package:
            for po_line in line.purchase_line_id:
                if po_line.type == 'material':
                    if po_line.order_id.project_budget:
                        self.update_received_material_cs(line, po_line)
                        self.update_received_material_bd(line, po_line)
                    else:
                        self.update_received_material_cs(line, po_line)
                elif po_line.type == 'labour':
                    if po_line.order_id.project_budget:
                        self.update_received_labour_cs(line, po_line)
                        self.update_received_labour_bd(line, po_line)
                    else:
                        self.update_received_labour_cs(line, po_line)
                elif po_line.type == 'overhead':
                    if po_line.order_id.project_budget:
                        self.update_received_overhead_cs(line, po_line)
                        self.update_received_overhead_bd(line, po_line)
                    else:
                        self.update_received_overhead_cs(line, po_line)
                elif po_line.type == 'equipment':
                    if po_line.order_id.project_budget:
                        self.update_received_equipment_cs(line, po_line)
                        self.update_received_equipment_bd(line, po_line)
                    else:
                        self.update_received_equipment_cs(line, po_line)
        return res


class RFQEquipmentLine(models.Model):
    _name = 'rfq.budget.gop.line'
    _description = "Group of Product Budget Line"
    _order = "sequence"

    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")

    cs_material_gop_id = fields.Many2one('material.gop.material', string='CS Material GOP ID')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', string='CS Labour GOP ID')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', string='CS Overhead GOP ID')
    cs_equipment_gop_id = fields.Many2one('material.gop.equipment', string='CS Equipment ID')
    
    bd_material_gop_id = fields.Many2one('budget.gop.material', string='BD Material GOP ID')
    bd_labour_gop_id = fields.Many2one('budget.gop.labour', string='BD Labour GOP ID')
    bd_overhead_gop_id = fields.Many2one('budget.gop.overhead', string='BD Overhead GOP ID')
    bd_equipment_gop_id = fields.Many2one('budget.gop.equipment', string='BD Equipment GOP ID')
    
    bd_material_gop_ids = fields.Many2many('budget.gop.material', string='BD Material GOP IDS')
    bd_labour_gop_ids = fields.Many2many('budget.gop.labour', string='BD Labour GOP IDS')
    bd_overhead_gop_ids = fields.Many2many('budget.gop.overhead', string='BD Overhead GOP IDS')
    bd_equipment_gop_ids = fields.Many2many('budget.gop.equipment', string='BD Equipment GOP IDS')

    cs_subcon_gop_id = fields.Many2one('material.gop.subcon', 'CS Subcon ID')
    bd_subcon_gop_id = fields.Many2one('budget.gop.subcon', 'BD Subcon ID')

    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('split', 'Split')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    gop_amount_total = fields.Float(string='Budgeted Amount', default=0.00)
    budgeted_amt_left = fields.Float('Budgeted Amount Left', default=0.00)
    billed_amt = fields.Float('Billed Amount', default=0.00)
    purchased_amt = fields.Float('Purchased Amount', default=0.00)
    is_reserved = fields.Boolean('Reserved', default=False)
    currency_id = fields.Many2one("res.currency", string="Currency")
    company_id = fields.Many2one(related='purchase_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)

    project = fields.Many2one(related='purchase_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('purchase_id.gop_budget_ids', 'purchase_id.gop_budget_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.purchase_id.gop_budget_ids:
                no += 1
                l.sr_no = no

    @api.onchange('type', 'purchase_id.is_multiple_budget', 'project_scope', 'section_name', 'group_of_product')
    def _onchange_product(self):
        for line in self:
            if line.purchase_id.budgeting_method == 'gop_budget':
                if line.project_scope and line.section_name and line.group_of_product:
                    if line.type == 'material':
                        line.cs_material_gop_id = False
                        line.bd_material_gop_id = False
                        line.bd_material_gop_ids = False
                        line.cs_material_gop_id = self.env['material.gop.material'].search(
                            [('job_sheet_id', '=', line.purchase_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section_name.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.purchase_id.is_multiple_budget == False:
                            if line.purchase_id.project_budget:
                                line.bd_material_gop_id = self.env['budget.gop.material'].search(
                                    [('budget_id', '=', line.purchase_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section_name.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budgeted_amt_left = line.bd_material_gop_id.amt_left
                            else:
                                line.budgeted_amt_left = line.cs_material_gop_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.gop.material'].search(
                                [('budget_id', 'in', line.purchase_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section_name.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budgeted_amt_left += bud.amt_left
                            else:
                                line.budgeted_amt_left = 0

                            line.bd_material_gop_ids = budget_ids

                    if line.type == 'labour':
                        line.cs_labour_gop_id = False
                        line.bd_labour_gop_id = False
                        line.bd_labour_gop_ids = False
                        line.cs_labour_gop_id = self.env['material.gop.labour'].search(
                            [('job_sheet_id', '=', line.purchase_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section_name.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.purchase_id.is_multiple_budget == False:
                            if line.purchase_id.project_budget:
                                line.bd_labour_gop_id = self.env['budget.gop.labour'].search(
                                    [('budget_id', '=', line.purchase_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section_name.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budgeted_amt_left = line.bd_labour_gop_id.amt_left
                            else:
                                line.budgeted_amt_left = line.cs_labour_gop_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.gop.labour'].search(
                                [('budget_id', 'in', line.purchase_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section_name.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budgeted_amt_left += bud.amt_left
                            else:
                                line.budgeted_amt_left = 0

                            line.bd_labour_gop_ids = budget_ids

                    if line.type == 'overhead':
                        line.cs_overhead_gop_id = False
                        line.bd_overhead_gop_id = False
                        line.bd_overhead_gop_ids = False
                        line.cs_overhead_gop_id = self.env['material.gop.overhead'].search(
                            [('job_sheet_id', '=', line.purchase_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section_name.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.purchase_id.is_multiple_budget == False:
                            if line.purchase_id.project_budget:
                                line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search(
                                    [('budget_id', '=', line.purchase_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section_name.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budgeted_amt_left = line.bd_overhead_gop_id.amt_left
                            else:
                                line.budgeted_amt_left = line.cs_overhead_gop_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.gop.overhead'].search(
                                [('budget_id', '=', line.purchase_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section_name.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budgeted_amt_left += bud.amt_left
                            else:
                                line.budgeted_amt_left = 0

                            line.bd_overhead_gop_ids = budget_ids

                    if line.type == 'equipment':
                        line.cs_equipment_gop_id = False
                        line.bd_equipment_gop_id = False
                        line.bd_equipment_gop_ids = False
                        line.cs_equipment_gop_id = self.env['material.gop.equipment'].search(
                            [('job_sheet_id', '=', line.purchase_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section_name.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.purchase_id.is_multiple_budget == False:
                            if line.purchase_id.project_budget:
                                line.bd_equipment_gop_id = self.env['budget.gop.equipment'].search(
                                    [('budget_id', '=', line.purchase_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section_name.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budgeted_amt_left = line.bd_equipment_gop_id.amt_left
                            else:
                                line.budgeted_amt_left = line.cs_equipment_gop_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.gop.equipment'].search(
                                [('budget_id', '=', line.purchase_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section_name.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budgeted_amt_left += bud.amt_left
                            else:
                                line.budgeted_amt_left = 0

                            line.bd_equipment_gop_ids = budget_ids