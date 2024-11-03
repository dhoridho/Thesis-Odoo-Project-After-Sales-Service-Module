# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, date

class PurchaseRequestWarning(models.TransientModel):
    _name = "purchase.request.warning"
    _description = "Purchase Request Warning"
    
    def default_get(self, fields):
        context = self._context
        result = super(PurchaseRequestWarning, self).default_get(fields)
        if context.get('warning_line_ids', []):
            result['warning_line_ids'] = context.get('warning_line_ids')
        return result
    
    name = fields.Html('Name')
    warning_line_ids = fields.One2many('purchase.request.warning.line', 'warning_id', 'Product Details')
    
    def confirm_purchase_request(self):
        context = self._context
        active_id = context.get('active_id')
        active_model = context.get('active_model')
        if active_model == 'purchase.request':
            purchase_request = self.env['purchase.request'].browse([active_id])
            if purchase_request.is_overbudget_approval_matrix_request:
                if purchase_request.approval_overbudget_matrix_id:
                    purchase_request.send_email_request_approval()
                    return purchase_request.write({'state': 'over_budget_approval', 'overbudget_pr_state': 'overbudget_pr'})
                elif not purchase_request.approval_overbudget_matrix_id:
                    raise UserError(_("Overbudget PR Approval Matrix not found, please check the matrix data!"))
            else:
                if purchase_request.is_approval_matrix_request:
                    purchase_request.send_email_request_approval()
                    purchase_request.write({'state':'to_approve'})
                else:
                    purchase_request.button_confirm_pr()
            # else:
                # for line in self.warning_line_ids:
                #     if line.realized_amount > line.available_budget:
                #         raise UserError(_("You Cannot Confirm Purchase Request, Realized Budget is Greater than Available Budget or Reserve Amount is not available,"
                #                           "Please Reject This Purchase Request or ask for Purchase Budget Change Request"))
                                          
                # return self.env['purchase.request'].browse([active_id]).button_to_approved()
                # return self.env['purchase.request'].browse([active_id]).write({'state': 'to_approve'})
            
        if active_model == 'purchase.order':
            purchase_order = self.env['purchase.order'].browse([active_id])
            purchase_order.write({'is_budget_confirmed': True})

            if purchase_order.is_overbudget_approval_matrix_order:
                if purchase_order.approval_overbudget_matrix_id:
                    return purchase_order.write({'state': 'over_budget_approval', 'overbudget_po_state': 'overbudget_po'})
                elif not purchase_order.approval_overbudget_matrix_id:
                    raise UserError(_("Overbudget PO Approval Matrix not found, please check the matrix data!"))
            else:
                return purchase_order.button_confirm()
            
        
class PurchaseRequestWarningLine(models.TransientModel):
    _name = "purchase.request.warning.line"
    _description = "Purchase Request Line Warning"
    
    warning_id = fields.Many2one('purchase.request.warning', 'Warning')
    product_id = fields.Many2one('product.product', "Product")
    purchase_req_budget = fields.Float("Purchase Budget")
    available_budget = fields.Float("Available to Reserve")
    reserved_budget = fields.Float("Reserved Budget")
    realized_amount = fields.Float("Realized Budget")
    remaining_amount = fields.Float("Remaining Budget")
        


                     
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    # def action_confirm_purchase_order(self):
    #     for order in self:        
    #         warning_line_ids = []
    #         overbudget = False
    #         for line in order.order_line:
    #             if (line.purchase_req_budget > 0 or line.realized_amount > 0) and line.price_subtotal > (line.purchase_req_budget - line.realized_amount):
    #                 overbudget = True
    #                 warning_line_ids.append((0,0,{'product_id':line.product_id.id, 'purchase_req_budget':round(line.purchase_req_budget,2), 'realized_amount':round(line.realized_amount,2)}))
    #         if overbudget:
    #             actions = self.env['ir.actions.act_window']._for_xml_id('equip3_accounting_budget.action_purchase_request_warning')
    #             actions.update({'context' : {'warning_line_ids' : warning_line_ids}})
    #             return actions
            
    #         order.button_confirm()
    #     return

    is_budget_confirmed = fields.Boolean(default=False, copy=False)
    state = fields.Selection(selection_add=[('over_budget_approval', 'Over Budget Approval'),('purchase', 'Purchase Order')], ondelete={'over_budget_approval': 'cascade', 'purchase': 'cascade'})
    overbudget_po_state = fields.Selection([
        ('overbudget_po', 'Overbudget PO'),
        ('overbudget_approved', 'Overbudget Approved'),
    ], 'Overbudget PO Status', readonly=True, copy=False, tracking=True)
    approval_overbudget_matrix_id = fields.Many2one(
        'approval.matrix.purchase.order.overbudget', string="Approval Matrix", compute='_get_approval_overbudget_matrix')
    approved_overbudget_matrix_ids = fields.One2many(
        'approval.matrix.purchase.order.overbudget.line', 'order_id', string="Approved Matrix")
    approval_overbudget_matrix_line_id = fields.Many2one(
        'approval.matrix.purchase.order.overbudget.line', string='Approval Matrix Line', compute='_get_overbudget_approve_button', store=False)
    is_overbudget_approve_button = fields.Boolean(string='Is Overbudget Approve Button', compute='_get_overbudget_approve_button', store=False)
    approval_overbudget_user_ids = fields.Many2many('res.users', 'overbudget_user_rel', string="User", compute='_compute_approval_overbudget_user_ids', store=True)
    is_overbudget_approval_matrix_order = fields.Boolean(compute="_compute_is_overbudget_approval_matrix_order", string="Overbudget Approving Matrix")
    is_allow_purchase_budget = fields.Boolean(string="Allow Purchase Budget", compute="_compute_is_allow_purchase_budget")


    @api.depends('company_id')
    def _compute_is_allow_purchase_budget(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            record.is_allow_purchase_budget = IrConfigParam.get_param('is_allow_purchase_budget', False)
    
    def _compute_is_overbudget_approval_matrix_order(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval = IrConfigParam.get_param('is_purchase_order_overbudget_approval_matrix')
        for record in self:
            record.is_overbudget_approval_matrix_order = approval

    def button_confirm(self):
        for order in self:
            warning_line_ids = order.check_overbudget()
            if warning_line_ids and not order.is_budget_confirmed:
                actions = self.env['ir.actions.act_window']._for_xml_id('equip3_accounting_budget.action_purchase_request_warning')
                actions.update({'context' : {'warning_line_ids' : warning_line_ids}})
                return actions
        return super(PurchaseOrder, self).button_confirm()

    def action_request_approval(self):
        for order in self:
            warning_line_ids = order.check_overbudget()
            if warning_line_ids and not order.is_budget_confirmed:
                actions = self.env['ir.actions.act_window']._for_xml_id('equip3_accounting_budget.action_purchase_request_warning')
                actions.update({'context' : {'warning_line_ids' : warning_line_ids}})
                return actions
            else:
                res = super(PurchaseOrder, self).action_request_approval()
                return res

    def check_overbudget(self):
        for order in self:
            warning_line_ids = []
            if order.is_allow_purchase_budget:
                for line in order.order_line:
                    if line.product_template_id.is_use_purchase_budget:
                        line.is_use_purchase_budget = True
                        subtotal_cost_same_budget = 0
                        if line.purchase_req_budget > 0 or line.realized_amount > 0:
                            if line.product_template_id.group_product:
                                for line2 in order.order_line:
                                    if line2.product_template_id.group_product.id == line.product_template_id.group_product.id and line2.purchase_req_budget == line.purchase_req_budget:
                                        subtotal_cost_same_budget += line2.price_subtotal
                            else:
                                subtotal_cost_same_budget = line.price_subtotal

                            if subtotal_cost_same_budget > (line.purchase_req_budget - line.realized_amount):
                                purchase_req_budget = round(line.purchase_req_budget,2)
                                available_budget = round(line.available_budget,2)
                                realized_amount = round(line.realized_amount + line.price_subtotal,2)
                                remaining_amount = purchase_req_budget - realized_amount
                                warning_line_ids.append((0,0,{'product_id':line.product_id.id, 'purchase_req_budget':purchase_req_budget, 'realized_amount':realized_amount, 'remaining_amount': remaining_amount, 'available_budget': available_budget}))
                        else:
                            raise UserError(_("There are no purchase budget for this product '%s'!" % line.product_template_id.name))

        return warning_line_ids

    def button_reject_overbudget_po(self):
        return self.write({'state':'reject', 'overbudget_po_state':'overbudget_po'})

    def button_confirm_overbudget_po(self):
        for record in self:
            if record.is_overbudget_approve_button and record.approval_overbudget_matrix_line_id:
                approval_matrix_line_id = record.approval_overbudget_matrix_line_id
                user = self.env.user
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})

            if len(record.approved_overbudget_matrix_ids) == len(record.approved_overbudget_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'overbudget_po_state':'overbudget_approved'})
                record.button_confirm()

    @api.onchange('approval_overbudget_matrix_id')
    def _compute_approving_overbudget_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft':
                counter = 1
                record.approved_overbudget_matrix_ids = []
                for rec in record.approval_overbudget_matrix_id:
                    for line in rec.approval_matrix_purchase_order_overbudget_line_ids:
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approver': line.minimum_approver,
                        }))
                        counter += 1
                record.approved_overbudget_matrix_ids = data

    @api.depends('order_line.price_unit', 'company_id', 'branch_id')
    def _get_approval_overbudget_matrix(self):
        for record in self:
            price_unit = 0
            avail_amount_budget = 0
            differece_amount = 0
            for line in record.order_line:
                price_unit = line.price_unit
                avail_amount_budget = line.purchase_req_budget
                differece_amount += abs(price_unit - avail_amount_budget)
            matrix_id = self.env['approval.matrix.purchase.order.overbudget'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_difference_amount', '<=', differece_amount),
                ('max_difference_amount', '>=', differece_amount),
            ], limit=1)

            record.approval_overbudget_matrix_id = matrix_id
            record._compute_approving_overbudget_matrix_lines()

    def _get_overbudget_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_overbudget_matrix_ids.filtered(
                lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_overbudget_approve_button = False
                record.approval_overbudget_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_overbudget_approve_button = True
                    record.approval_overbudget_matrix_line_id = matrix_line_id.id
                else:
                    record.is_overbudget_approve_button = False
                    record.approval_overbudget_matrix_line_id = False
            else:
                record.is_overbudget_approve_button = False
                record.approval_overbudget_matrix_line_id = False

    @api.depends('approved_overbudget_matrix_ids.user_ids')
    def _compute_approval_overbudget_user_ids(self):
        for record in self:
            user_ids = []
            for line in record.approved_overbudget_matrix_ids:
                user_ids += line.user_ids.ids

            record.approval_overbudget_user_ids = [(6, 0, user_ids)]
            
             
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    purchase_req_budget = fields.Float("Purchase Budget", compute='_get_purchase_req_budget')
    realized_amount = fields.Float("Realized Budget", compute='_get_purchase_req_budget')
    confirm_purchase_req_budget = fields.Float("Confirmed Purchase Request Budget")
    confirm_realized_amount = fields.Float("Confirmed Realized Budget")
    confirm_budget_data = fields.Boolean(default=False)
    purchase_budget_lines = fields.One2many('budget.purchase', 'purchase_lines_id', string='Purchase Budget Lines', store=True)
    available_budget = fields.Float("Available to Reserve", compute='_get_purchase_req_budget')
    remaining_budget = fields.Float("Remaining Budget", compute='_get_purchase_req_budget')
    is_use_purchase_budget = fields.Boolean('Is Use Purchase Budget', default=False)


    @api.onchange('product_template_id')
    def onchange_is_use_purchase_budget(self):
        for line in self:
            line.is_use_purchase_budget = line.product_template_id.is_use_purchase_budget

    @api.depends('product_id','analytic_tag_ids','order_id.date_planned','currency_id')
    def _get_purchase_req_budget(self):
        today = fields.Date.today()
        for rec in self:
            purchase_req_budget = 0
            realized_amount = 0
            available_budget = 0
            remaining_budget = 0

            order_date = rec.order_id.date_planned
            if rec.order_id.from_purchase_request:
                purchase_request = self.env['purchase.request'].search([('name','=',rec.order_id.origin)], limit=1)
                order_date = purchase_request.request_date

            if rec.confirm_budget_data:
                purchase_req_budget = rec.confirm_purchase_req_budget
                realized_amount = rec.confirm_realized_amount
            elif rec.product_id:
                domain = [
                    # '&', ('date_from', '<', request_date), ('date_to', '>', request_date),  # Overlapping condition
                    # '|',('date_from', '>', request_date), ('date_to', '<', request_date),  # Starting condition
                    ('account_tag_ids', 'in', rec.analytic_tag_ids.ids),
                    ('product_budget', '!=', False),
                    ('date_from', '<=', order_date), ('date_to', '>=', order_date),
                    ('product_id', '=', rec.product_id.id), ('purchase_budget_state', 'in', ('confirm','validate')),
                    ('purchase_budget_id.is_parent_budget','=',False),
                ]
                product_budget_lines = self.env['budget.purchase.lines'].search(domain)
                gop = rec.product_id.product_tmpl_id.group_product
                if product_budget_lines:
                    monthly_budget_purchase_lines = False
                    budget_purchase_lines = product_budget_lines
                elif gop:
                    domain = [('group_product_id','=',gop.id),('monthly_purchase_budget_id.date_from','<=',order_date),('monthly_purchase_budget_id.date_to','>=',order_date),('account_tag_ids','in',rec.analytic_tag_ids.ids)]
                    monthly_budget_purchase_lines = self.env['monthly.purchase.budget.line'].search(domain)

                    if not monthly_budget_purchase_lines:
                        budget_purchase_line_filter = [('purchase_budget_id.is_parent_budget','=',False),('group_product_id','=',gop.id),('date_from','<=',order_date),('date_to','>=',order_date),('account_tag_ids','in',rec.analytic_tag_ids.ids)]
                        budget_purchase_lines = self.env['budget.purchase.lines'].search(budget_purchase_line_filter)
                else:
                    domain = [('product_id','=',rec.product_id.id),('monthly_purchase_budget_id.date_from','<=',order_date),('monthly_purchase_budget_id.date_to','>=',order_date),('account_tag_ids','in',rec.analytic_tag_ids.ids)]
                    monthly_budget_purchase_lines = self.env['monthly.purchase.budget.line'].search(domain)

                    if not monthly_budget_purchase_lines:
                        budget_purchase_line_filter = [('purchase_budget_id.is_parent_budget','=',False),('product_id','=',rec.product_id.id),('date_from','<=',order_date),('date_to','>=',order_date),('account_tag_ids','in',rec.analytic_tag_ids.ids)]
                        budget_purchase_lines = self.env['budget.purchase.lines'].search(budget_purchase_line_filter)

                if monthly_budget_purchase_lines:
                    purchase_req_budget = sum([x.currency_id._convert(x.planned_amount, rec.currency_id, rec.company_id, order_date) for x in monthly_budget_purchase_lines if x.monthly_purchase_budget_id.state in ('done','validate')]) or 0
                    realized_amount = sum([x.currency_id._convert(x.practical_amount, rec.currency_id, rec.company_id, order_date) for x in monthly_budget_purchase_lines if x.monthly_purchase_budget_id.state in ('done','validate')]) or 0
                    available_budget = sum([x.currency_id._convert(x.avail_amount, rec.currency_id, rec.company_id, order_date) for x in monthly_budget_purchase_lines if x.monthly_purchase_budget_id.state in ('done','validate')]) or 0
                    remaining_budget = sum([x.currency_id._convert(x.remaining_amount, rec.currency_id, rec.company_id, order_date) for x in monthly_budget_purchase_lines if x.monthly_purchase_budget_id.state in ('done','validate')]) or 0
                else:
                    purchase_req_budget = budget_purchase_lines and sum([x.currency_id._convert(x.planned_amount, rec.currency_id, rec.company_id, order_date) for x in budget_purchase_lines if x.purchase_budget_id.state in ('done','validate')]) or 0
                    realized_amount = budget_purchase_lines and sum([x.currency_id._convert(x.practical_amount, rec.currency_id, rec.company_id, order_date) for x in budget_purchase_lines if x.purchase_budget_id.state in ('done','validate')]) or 0
                    available_budget = budget_purchase_lines and sum([x.currency_id._convert(x.avail_amount, rec.currency_id, rec.company_id, order_date) for x in budget_purchase_lines if x.purchase_budget_id.state in ('done','validate')]) or 0
                    remaining_budget = budget_purchase_lines and sum([x.currency_id._convert(x.remaining_amount, rec.currency_id, rec.company_id, order_date) for x in budget_purchase_lines if x.purchase_budget_id.state in ('done','validate')]) or 0
            
            rec.purchase_req_budget = purchase_req_budget
            rec.realized_amount = realized_amount
            rec.available_budget = available_budget
            rec.remaining_budget = remaining_budget
        
    
class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    state = fields.Selection(selection_add=[('over_budget_approval', 'Over Budget Approval'),('to_approve', 'Waiting For Approval')], ondelete={'over_budget_approval': 'cascade', 'to_approve': 'cascade'})
    overbudget_pr_state = fields.Selection([
        ('overbudget_pr', 'Overbudget PR'),
        ('overbudget_approved', 'Overbudget Approved'),
    ], 'Overbudget PR Status', readonly=True, copy=False, tracking=True)
    approval_overbudget_matrix_id = fields.Many2one(
        'approval.matrix.purchase.request.overbudget', string="Approval Matrix", compute='_get_approval_overbudget_matrix')
    approved_overbudget_matrix_ids = fields.One2many(
        'approval.matrix.purchase.request.overbudget.line', 'request_id', string="Approved Matrix")
    approval_overbudget_matrix_line_id = fields.Many2one(
        'approval.matrix.purchase.request.overbudget.line', string='Approval Matrix Line', compute='_get_overbudget_approve_button', store=False)
    is_overbudget_approve_button = fields.Boolean(string='Is Overbudget Approve Button', compute='_get_overbudget_approve_button', store=False)
    # approvers_ids = fields.Many2many('res.users', 'purchase_request_budget_approvers_rel', string='Approvers List')
    approval_overbudget_user_ids = fields.Many2many('res.users', string="User", compute='_compute_approval_overbudget_user_ids', store=True)
    is_overbudget_approval_matrix_request = fields.Boolean(compute="_compute_is_overbudget_approval_matrix_request", string="Overbudget Approving Matrix")
    is_allow_purchase_budget = fields.Boolean(string="Allow Purchase Budget", compute="_compute_is_allow_purchase_budget")


    @api.depends('company_id')
    def _compute_is_allow_purchase_budget(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            record.is_allow_purchase_budget = IrConfigParam.get_param('is_allow_purchase_budget', False)

    def _compute_is_overbudget_approval_matrix_request(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval = IrConfigParam.get_param('is_purchase_request_overbudget_approval_matrix')
        for record in self:
            record.is_overbudget_approval_matrix_request = approval

    def check_overbudget(self):
        for req in self:
            exceeding_lines = []
            if req.is_allow_purchase_budget:
                for line in req.line_ids:
                    if line.product_id.product_tmpl_id.is_use_purchase_budget:
                        line.is_use_purchase_budget = True
                        if line.purchase_req_budget_2 != 0:
                            subtotal_cost_same_budget = 0
                            if line.product_id.group_product:
                                for line2 in req.line_ids:
                                    if line2.product_id.group_product.id == line.product_id.group_product.id and line2.avail_amount_budget == line.avail_amount_budget:
                                        subtotal_cost_same_budget += line2.price_total
                            else:
                                subtotal_cost_same_budget = line.price_total
                            # if line.price_total > line.remaining_amount_budget:
                            if subtotal_cost_same_budget > line.avail_amount_budget:
                                purchase_req_budget = round(line.purchase_req_budget_2,2)
                                available_budget = round(line.avail_amount_budget,2)
                                reserved_budget = round(line.reserve_amount_budget,2)
                                remaining_amount = round(line.remaining_amount_budget,2)
                                realized_amount = round(line.realized_amount + line.price_total,2)
                                exceeding_lines.append((0,0,{'product_id':line.product_id.id, 
                                                             'purchase_req_budget':purchase_req_budget, 
                                                              'available_budget':available_budget,
                                                                'reserved_budget':reserved_budget, 
                                                                  'realized_amount':realized_amount, 
                                                                    'remaining_amount': remaining_amount}))
                        else:
                            raise UserError(_("There are no purchase budget for this product '%s'!" % line.product_id.name))

        return exceeding_lines

    def button_to_approve(self):
        for req in self:
            exceeding_lines = req.check_overbudget()

            if exceeding_lines:
                return {
                    'name': _('Warning'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.request.warning',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                    'context': {'default_name': 'Warning', 'default_warning_line_ids': exceeding_lines}
                }
            else:
                res = super(PurchaseRequest, self).button_to_approve()
                return res

    def action_confirm_purchase_request(self):
        for req in self:
            exceeding_lines = req.check_overbudget()

            if exceeding_lines:
                return {
                    'name': _('Warning'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.request.warning',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                    'context': {'default_name': 'Warning', 'default_warning_line_ids': exceeding_lines}
                }
            else:
                res = super(PurchaseRequest, self).action_confirm_purchase_request()
                return res
        
    def button_reject_overbudget_pr(self):
        return self.write({'state':'rejected', 'overbudget_pr_state':'overbudget_pr'})

    def button_confirm_overbudget_pr(self):
        for record in self:
            if record.is_overbudget_approve_button and record.approval_overbudget_matrix_line_id:
                approval_matrix_line_id = record.approval_overbudget_matrix_line_id
                user = self.env.user
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        # next_approval_matrix_line_id = sorted(record.approved_overbudget_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        # approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
                        # if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                        #     for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                        #         ctx = {
                        #             'email_from': self.env.user.company_id.email,
                        #             'email_to': approving_matrix_line_user.partner_id.email,
                        #             'user_name': approving_matrix_line_user.name,
                        #             'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                        #             'url': url,
                        #             'submitter' : approver_name,
                        #             'product_lines': data,
                        #             'date': date.today(),
                        #         }
                        #         if is_email_notification_req:
                        #             template_id.sudo().with_context(ctx).send_mail(record.id, True)
                        #         if is_whatsapp_notification_req:
                        #             phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                        #             # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                        #             record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user,
                        #                                                    phone_num, url, submitter=approver_name)
                        # else:
                        #     if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                        #         ctx = {
                        #             'email_from': self.env.user.company_id.email,
                        #             'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                        #             'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                        #             'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                        #             'url': url,
                        #             'submitter' : approver_name,
                        #             'product_lines': data,
                        #             'date': date.today(),
                        #         }
                        #         if is_email_notification_req:
                        #             template_id.sudo().with_context(ctx).send_mail(record.id, True)
                        #         if is_whatsapp_notification_req:
                        #             phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                        #             # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
                        #             record._send_qiscus_whatsapp_approval(wa_template_id,
                        #                                                    next_approval_matrix_line_id[0].user_ids[0],
                        #                                                    phone_num, url, submitter=approver_name)

                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})

            if len(record.approved_overbudget_matrix_ids) == len(record.approved_overbudget_matrix_ids.filtered(lambda r:r.approved)):
                if record.is_approval_matrix_request:
                    record.send_email_request_approval()
                    record.write({'state':'to_approve', 'overbudget_pr_state':'overbudget_approved'})
                else:
                    record.write({'overbudget_pr_state':'overbudget_approved'})
                    record.button_confirm_pr()


    @api.onchange('approval_overbudget_matrix_id')
    def _compute_approving_overbudget_matrix_lines(self):
        data = [(5, 0, 0)]
        # approver_list = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft':
                counter = 1
                record.approved_overbudget_matrix_ids = []
                # approver_list = []
                for rec in record.approval_overbudget_matrix_id:
                    for line in rec.approval_matrix_purchase_request_overbudget_line_ids:
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approver': line.minimum_approver,
                        }))
                        counter += 1
                        # for approvers in line.user_ids:
                        #     approver_list.append(approvers.id)
                record.approved_overbudget_matrix_ids = data
                # record.approvers_ids = approver_list

    @api.depends('line_ids.price_total', 'company_id', 'branch_id')
    def _get_approval_overbudget_matrix(self):
        for record in self:
            estimated_cost = 0
            avail_amount_budget = 0
            differece_amount = 0
            for line in record.line_ids:
                estimated_cost = line.price_total
                avail_amount_budget = line.avail_amount_budget
                differece_amount += abs(estimated_cost - avail_amount_budget)
            matrix_id = self.env['approval.matrix.purchase.request.overbudget'].search([
                ('company_id', '=', record.company_id.id),
                ('branch_id', '=', record.branch_id.id),
                ('min_difference_amount', '<=', differece_amount),
                ('max_difference_amount', '>=', differece_amount),
            ], limit=1)

            record.approval_overbudget_matrix_id = matrix_id
            record._compute_approving_overbudget_matrix_lines()

    def _get_overbudget_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_overbudget_matrix_ids.filtered(
                lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_overbudget_approve_button = False
                record.approval_overbudget_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_overbudget_approve_button = True
                    record.approval_overbudget_matrix_line_id = matrix_line_id.id
                else:
                    record.is_overbudget_approve_button = False
                    record.approval_overbudget_matrix_line_id = False
            else:
                record.is_overbudget_approve_button = False
                record.approval_overbudget_matrix_line_id = False

    @api.depends('approved_overbudget_matrix_ids.user_ids')
    def _compute_approval_overbudget_user_ids(self):
        for request in self:
            user_ids = []
            for line in request.approved_overbudget_matrix_ids:
                user_ids += line.user_ids.ids

            request.approval_overbudget_user_ids = [(6, 0, user_ids)]


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    po_actual_amount = fields.Float('PO Actual Amount', compute="_compute_po_actual_amount")
    is_use_purchase_budget = fields.Boolean('Is Use Purchase Budget', default=False)


    @api.depends('purchase_lines', 'purchase_lines.state')
    def _compute_po_actual_amount(self):
        for line in self:
            purchase_lines = line.purchase_lines.filtered(lambda po_line: po_line.state in ('purchase', 'done'))
            line.po_actual_amount = 0
            if purchase_lines:
                line.po_actual_amount = sum(purchase_lines.mapped('price_subtotal'))

    @api.onchange('product_id')
    def onchange_is_use_purchase_budget(self):
        for line in self:
            line.is_use_purchase_budget = line.product_id.product_tmpl_id.is_use_purchase_budget