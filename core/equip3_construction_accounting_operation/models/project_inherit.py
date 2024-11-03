from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date

# class AnalyticGroupInheriy(models.Model):
#     _inherit = 'account.analytic.tag'

#     project_id = fields.Many2one('project.project', string='Project')

class ProjectInherited(models.Model):
    _inherit = 'project.project'

    #flexible claim retention
    flexible_reten = fields.Boolean(string='Flexible Claim Retention', default=False)
    cancel_date = fields.Datetime(string="Cancellation Date")

    @api.model
    def create(self, vals):
        project = super(ProjectInherited, self).create(vals)
    
        # add analytic account to all analytic group
        is_default_analytic_group = self.env['ir.config_parameter'].sudo().get_param('is_create_default_analytic_group')
        if is_default_analytic_group:
            project.analytic_idz = [(0, 0, {
                'name': project.name
            })]
            if not project.analytic_account_id:
                project._create_analytic_account()
            for rec in project.analytic_idz:
                if project.analytic_account_id.id not in [x.account_id.id for x in rec.analytic_distribution_ids]:
                    rec.analytic_distribution_ids = [(0, 0, {
                        'account_id': project.analytic_account_id.id
                    })]
                       
        return project

    def write(self, values):
        
        is_default_analytic_group = self.env['ir.config_parameter'].sudo().get_param('is_create_default_analytic_group')
        if is_default_analytic_group and values.get('analytic_idz'):
            if type(values.get('analytic_idz')[0]) == list:
                # validation default analytic group
                default_analytic_group = self.env['account.analytic.tag'].search([('name', '=', self.name)])
                check_exist_default_analytic_group = [x for x in default_analytic_group.ids if x in values['analytic_idz'][0][2]]
                if not check_exist_default_analytic_group:
                    raise ValidationError("Default analytic group cannot be delete") 
            
                # remove analytic account for removed analytic group
                for rec in self.analytic_idz:
                    if rec.id not in values['analytic_idz'][0][2]:
                        for analytic_line in rec.analytic_distribution_ids:
                            if analytic_line.account_id.id == self.analytic_account_id.id:
                                analytic_line.unlink()
        
        record = super(ProjectInherited, self).write(values)
        
        # add analytic account for added analytic group
        if is_default_analytic_group and values.get('analytic_idz'):
            if type(values.get('analytic_idz')[0]) == list:              
                for rec in self.analytic_idz:
                    if self.analytic_account_id.id not in [x.account_id.id for x in rec.analytic_distribution_ids]:
                        rec.analytic_distribution_ids = [(0, 0, {
                            'account_id': self.analytic_account_id.id
                        })]
                        
        return record

    def _get_cip(self):
        return self.env['account.account'].search([('name', '=', 'Construction In Progress')])
    
    def _get_revenue(self):
        return self.env['account.account'].search([('name', '=','Revenue')], limit=1).id

    def _get_down_payment(self):
        return self.env['account.account'].search([('name', '=','Unearned Revenue')], limit=1).id

    def _get_accrued_revenue(self):
        return self.env['account.account'].search([('name', '=','Accrued Revenue')], limit=1).id

    def _get_retention(self):
        return self.env['account.account'].search([('name', '=','Retention Receivable')], limit=1).id

    def _get_penalty_receivable(self):
        return self.env['account.account'].search([('name', '=','Revenue of Penalty')], limit=1).id

    cip_account_id = fields.Many2one(comodel_name='account.account', string="Construction In Progress", default=_get_cip)
    receivable_id = fields.Many2one(comodel_name='account.account', string='Receivable')
    revenue_id = fields.Many2one(comodel_name='account.account', string='Revenue', default=_get_revenue)
    down_payment_id = fields.Many2one(comodel_name='account.account', string='Down Payment', default=_get_down_payment)
    accrued_id = fields.Many2one(comodel_name='account.account', string='Claim Request', default=_get_accrued_revenue)
    retention_id = fields.Many2one(comodel_name='account.account', string='Retention', default=_get_retention)
    income_tax_id = fields.Many2one(comodel_name='account.account', string='Income Tax')
    vat_tax_id = fields.Many2one(comodel_name='account.account', string='VAT Tax')
    penalty_receivable = fields.Many2one(comodel_name='account.account', string='Penalty Receivable', default=_get_penalty_receivable)

    def _get_down_payment_account(self):
        return self.env['account.account'].search([('name', '=','Advance (Subcon)')], limit=1).id

    def _get_cost_account(self):
        return self.env['account.account'].search([('name', '=','Cost of Revenue')], limit=1).id

    def _get_accrued_account(self):
        return self.env['account.account'].search([('name', '=','Contract Liabilities')], limit=1).id

    def _get_retention_account(self):
        return self.env['account.account'].search([('name', '=','Retention Payable')], limit=1).id
    
    def _get_penalty_payable(self):
        return self.env['account.account'].search([('name', '=','Expense of Penalty')], limit=1).id

    payable_account = fields.Many2one(comodel_name='account.account', string='Account Payable')
    income_taxes_account = fields.Many2one(comodel_name='account.account', string='Income Tax')
    vat_account = fields.Many2one(comodel_name='account.account', string='VAT Tax')
    down_payment_account = fields.Many2one(comodel_name='account.account', string='Down Payment', default=_get_down_payment_account)
    cost_account = fields.Many2one(comodel_name='account.account', string='Cost of Revenue', default=_get_cost_account)
    accrued_account = fields.Many2one(comodel_name='account.account', string='Claim Request', default=_get_accrued_account)
    retention_account = fields.Many2one(comodel_name='account.account', string='Retention', default=_get_retention_account)
    penalty_payable = fields.Many2one(comodel_name='account.account', string='Penalty Payable', default=_get_penalty_payable)
    
    hide_amount_client = fields.Boolean(string='Hide Amount Client', default=False, 
        compute='_compute_hide_amount_client' )
    
    @api.depends('amount', 'amount_client')
    def _compute_hide_amount_client(self):
        for record in self:
            if record.diff_penalty == True:
                if record.amount == 0.0 and record.amount_client == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0 or record.amount_client > 0.0:
                    record.hide_amount_client = False
            else:
                if record.amount == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0:
                    record.hide_amount_client = False
    
    def button_complete(self):
        """
        Set state to complete for current project
        """
        progress_claim_ids = self.env['progressive.claim'].search([('project_id', '=', self.id), ('state', '!=', 'done')])

        if progress_claim_ids:
            return{             
                'type': 'ir.actions.act_window',
                'name': 'Complete Project',
                'view_mode': 'form', 
                'target': 'new',
                'res_model': 'complete.project.wizard',
                'context': {'default_project_id': self.id,
                }
            }
        else:
            return{             
                'type': 'ir.actions.act_window',
                'name': 'Complete Project',
                'view_mode': 'form', 
                'target': 'new',
                'res_model': 'complete.project.wizard.date'
            }

    def button_cancel(self):
        """
        Set state to cancel for current project
        """

        return{             
                'type': 'ir.actions.act_window',
                'name': 'Cancel Project',
                'view_mode': 'form', 
                'target': 'new',
                'res_model': 'cancel.project.wizard',
                'context': {'default_project_id': self.id,
                            'default_department_type': self.department_type}
        }
    

    penalty_doc = fields.Many2one('account.move', string="Penalty Document", compute="_compute_penalty_doc")
    penalty_doc_exist = fields.Boolean(string="Penalty Document Exist", compute="_compute_penalty_doc", default=False)

    def _compute_penalty_doc(self):
        for res in self:
            if res.primary_states == 'cancelled':
                doc_file = self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', True), ('project_id', '=', res.id), ('cancelled_contract_so', '=', res.sale_order_main.id), ('state', 'not in', ('rejected','cancel','failed'))], limit=1)
                if doc_file:
                    res.write({'penalty_doc': doc_file.id,
                               'penalty_doc_exist': True})
                else:
                    res.write({'penalty_doc': False,
                               'penalty_doc_exist': False})
            else:
                res.write({'penalty_doc': False,
                           'penalty_doc_exist': False})

    def create_bill(self):
        penalty_fee = 0
        
        if self.method == 'percentage':
            penalty_fee = self.contract_amount * (self.amount / 100)
        elif self.method == 'fixed':
            penalty_fee = self.amount

        if not self.penalty_payable:
            raise ValidationError("Set account for penalty payable first.")
        else:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.partner_id.id,
                'project_id': self.id,
                'cancelled_contract_so': self.sale_order_main.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.analytic_idz])],
                'branch_id': self.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.penalty_payable.id,
                    'name': 'Penalty fee from contractor',
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.analytic_idz])],
                    'tax_ids': [(6, 0, [v.id for v in self.main_tax_id])],
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                })],
            })    

            return {
                'name': _('Bill Contractor'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': bill.id,
                'res_model': 'account.move',
                'target':'current',
            }

    def create_invoice(self):
        penalty_fee = 0

        if self.diff_penalty == True:
            if self.method_client == 'percentage':
                penalty_fee = self.contract_amount * (self.amount_client / 100)
            elif self.method_client == 'fixed':
                penalty_fee = self.amount_client
        else:
            if self.method == 'percentage':
                penalty_fee = self.contract_amount * (self.amount / 100)
            elif self.method == 'fixed':
                penalty_fee = self.amount

        if not self.penalty_receivable:
            raise ValidationError("Set account for penalty receivable first.")
        else:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.partner_id.id,
                'project_id': self.id,
                'cancelled_contract_so': self.sale_order_main.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.analytic_idz])],
                'branch_id': self.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.penalty_receivable.id,
                    'name': 'Penalty fee from client',
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.analytic_idz])],
                    'tax_ids': [(6, 0, [v.id for v in self.main_tax_id])],
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                })],
            })

            return {
                'name': _('Invoice Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'target':'current',
            }
    
class VariationOrderLineInherited(models.Model):
    _inherit = 'variation.order.line'
    
    responsible = fields.Selection(related='name.responsible', string='Responsible')
    reason = fields.Text(related='name.reason', string='Reason')
    state = fields.Selection(related="name.state", string='Status')
    penalty_doc = fields.Many2one('account.move', string="Penalty Document", compute="_compute_penalty_doc")
    penalty_doc_exist = fields.Boolean(string="Penalty Document Exist", compute="_compute_penalty_doc", default=False)
    hide_amount_client = fields.Boolean(string='Hide Amount Client', default=False, 
        compute='_compute_hide_amount_client' )
    cancel_date = fields.Datetime(string="Cancellation Date")
    project_cancel = fields.Boolean(string='Cancel Project', default=False, compute="_compute_project_cancel")

    @api.depends('project_id')
    def _compute_project_cancel(self):
        for record in self:
            if record.project_id.primary_states == 'cancelled':
                record.project_cancel = True
            else:
                record.project_cancel = False
    
    @api.depends('amount', 'amount_client')
    def _compute_hide_amount_client(self):
        for record in self:
            if record.diff_penalty == True:
                if record.amount == 0.0 and record.amount_client == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0 or record.amount_client > 0.0:
                    record.hide_amount_client = False
            else:
                if record.amount == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0:
                    record.hide_amount_client = False

    def _compute_penalty_doc(self):
        for res in self:
            if res.state == 'cancel':
                doc_file = self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', True), ('project_id', '=', res.project_id.id), ('cancelled_contract_so', '=', res.name.id), ('state', 'not in', ('rejected','cancel','failed'))], limit=1)
                if doc_file:
                    res.write({'penalty_doc': doc_file.id,
                               'penalty_doc_exist': True})
                else:
                    res.write({'penalty_doc': False,
                               'penalty_doc_exist': False})
            else:
                res.write({'penalty_doc': False,
                           'penalty_doc_exist': False})
        
    def button_cancel_contract(self):
        """
        Set state to cancel for selected contract
        """
        
        return{             
                'type': 'ir.actions.act_window',
                'name': 'Cancel Contract',
                'view_mode': 'form', 
                'target': 'new',
                'res_model': 'cancel.contract.wizard',
                'context': {'default_contract_id': self.id,
                            'default_project_id': self.project_id.id,
                            'default_department_type': self.project_id.department_type}
        }

    def create_bill(self):
        penalty_fee = 0
        if self.method == 'percentage':
            penalty_fee = self.contract_amount * (self.amount / 100)
        elif self.method == 'fix':
            penalty_fee = self.amount

        if not self.project_id.penalty_payable:
            raise ValidationError("Set account for penalty payable first.")
        else:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.name.partner_id.id,
                'project_id': self.project_id.id,
                'cancelled_contract_so': self.name.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.name.analytic_idz])],
                'branch_id': self.project_id.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.project_id.penalty_payable.id,
                    'name': 'Penalty fee from contractor',
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.name.analytic_idz])],
                    'tax_ids': [(6, 0, [v.id for v in self.tax_id])],
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                })],
            })

            return {
                'name': _('Bill Contractor'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': bill.id,
                'res_model': 'account.move',
                'target':'current',
            }

    def create_invoice(self):
        penalty_fee = 0

        if self.diff_penalty == True:
            if self.method_client == 'percentage':
                penalty_fee = self.contract_amount * (self.amount_client / 100)
            elif self.method_client == 'fix':
                penalty_fee = self.amount_client
        else:
            if self.method == 'percentage':
                penalty_fee = self.contract_amount * (self.amount / 100)
            elif self.method == 'fix':
                penalty_fee = self.amount

        if not self.project_id.penalty_receivable:
            raise ValidationError("Set account for penalty receivable first.")
        else:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.name.partner_id.id,
                'project_id': self.project_id.id,
                'cancelled_contract_so': self.name.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.name.analytic_idz])],
                'branch_id': self.project_id.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.project_id.penalty_receivable.id,
                    'name': 'Penalty fee from client',
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.name.analytic_idz])],
                    'tax_ids': [(6, 0, [v.id for v in self.tax_id])],
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                })],
            })

            return {
                'name': _('Invoice Client'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'target':'current',
            }

class ContractSubconInherit(models.Model):
    _inherit = 'contract.subcon.const'

    state = fields.Selection(related='name.state')
    penalty_id = fields.Many2one(related='name.penalty_id')
    diff_penalty = fields.Boolean(string='Different Penalty', related='name.diff_penalty')
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage', related='name.method')
    amount = fields.Float(string='Amount', related='name.amount')
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                                     default='percentage', related='name.method_client')
    amount_client = fields.Float(string='Amount', related='name.amount_client')
    responsible = fields.Selection(related='name.responsible', string='Responsible')
    reason = fields.Text(related='name.reason', string='Reason')
    penalty_doc = fields.Many2one('account.move', string="Penalty Document", compute="_compute_penalty_doc")
    penalty_doc_exist = fields.Boolean(string="Penalty Document Exist", compute="_compute_penalty_doc", default=False)
    hide_amount_client = fields.Boolean(string='Hide Amount Client', default=False, 
        compute='_compute_hide_amount_client' )
    cancel_date = fields.Datetime(string="Cancellation Date")
    stage_ids = fields.One2many(related="name.milestone_term_ids")
    
    @api.depends('amount', 'amount_client')
    def _compute_hide_amount_client(self):
        for record in self:
            if record.diff_penalty == True:
                if record.amount == 0.0 and record.amount_client == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0 or record.amount_client > 0.0:
                    record.hide_amount_client = False
            else:
                if record.amount == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0:
                    record.hide_amount_client = False

    def _compute_penalty_doc(self):
        for res in self:
            if res.state == 'cancel':
                doc_file = self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', True), ('project_id', '=', res.name.project.id), ('cancelled_contract_po', '=', res.name.id), ('state', 'not in', ('rejected','cancel','failed'))], limit=1)
                if doc_file:
                    res.write({'penalty_doc': doc_file.id,
                               'penalty_doc_exist': True})
                else:
                    res.write({'penalty_doc': False,
                               'penalty_doc_exist': False})
            else:
                res.write({'penalty_doc': False,
                           'penalty_doc_exist': False})
    

    def action_cancel(self):
        return{
            'name': 'Cancel Contract',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancel.contract.subcon',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_contract_subcon': self.id
            }
        }

    def create_bill(self):
        penalty_fee = 0

        if self.method == 'percentage':
            penalty_fee = self.contract_amount_subcon * (self.amount / 100)
        elif self.method == 'fixed':
            penalty_fee = self.amount

        if not self.project_id.penalty_payable:
            raise ValidationError("Set account for penalty payable first.")
        else:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.name.partner_id.id,
                'project_id': self.project_id.id,
                'cancelled_contract_po': self.name.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                'branch_id': self.project_id.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.project_id.penalty_payable.id,
                    'name': 'Penalty fee from contractor',
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                    'tax_ids': [(6, 0, [v.id for v in self.subcon_tax_id])],
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                })],
            })

            return {
                'name': _('Bill Contractor'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': bill.id,
                'res_model': 'account.move',
                'target':'current',
            }

    def create_invoice(self):
        penalty_fee = 0

        if self.diff_penalty == True:
            if self.method_client == 'percentage':
                penalty_fee = self.contract_amount_subcon * (self.amount_client / 100)
            elif self.method_client == 'fixed':
                penalty_fee = self.amount_client
        else:
            if self.method == 'percentage':
                penalty_fee = self.contract_amount * (self.amount / 100)
            elif self.method == 'fixed':
                penalty_fee = self.amount

        if not self.project_id.penalty_receivable:
            raise ValidationError("Set account for penalty receivable first.")
        else:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.name.partner_id.id,
                'project_id': self.project_id.id,
                'cancelled_contract_po': self.name.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                'branch_id': self.project_id.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.project_id.penalty_receivable.id,
                    'name': 'Penalty fee from vendor/subcon',
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                    'tax_ids': [(6, 0, [v.id for v in self.subcon_tax_id])],
                })],
            })

            return {
                'name': _('Invoice Vendor/Subcon'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'target':'current',
            }

class VariationOrderLineSubconInherit(models.Model):
    _inherit = 'variation.subcon.line'

    state = fields.Selection(related='name.state')
    penalty_id = fields.Many2one(related='name.penalty_id')
    diff_penalty = fields.Boolean(string='Different Penalty', related='name.diff_penalty')
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage', related='name.method')
    amount = fields.Float(string='Amount', related='name.amount')
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                                     default='percentage', related='name.method_client')
    amount_client = fields.Float(string='Amount', related='name.amount_client')
    responsible = fields.Selection(related='name.responsible', string='Responsible')
    reason = fields.Text(related='name.reason', string='Reason')
    penalty_doc = fields.Many2one('account.move', string="Penalty Document", compute="_compute_penalty_doc")
    penalty_doc_exist = fields.Boolean(string="Penalty Document Exist", compute="_compute_penalty_doc", default=False)
    hide_amount_client = fields.Boolean(string='Hide Amount Client', default=False, 
        compute='_compute_hide_amount_client' )
    cancel_date = fields.Datetime(string="Cancellation Date")
    
    @api.depends('amount', 'amount_client')
    def _compute_hide_amount_client(self):
        for record in self:
            if record.diff_penalty == True:
                if record.amount == 0.0 and record.amount_client == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0 or record.amount_client > 0.0:
                    record.hide_amount_client = False
            else:
                if record.amount == 0.0:
                    record.hide_amount_client = True
                elif record.amount > 0.0:
                    record.hide_amount_client = False

    def _compute_penalty_doc(self):
        for res in self:
            if res.state == 'cancel':
                doc_file = self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', True), ('project_id', '=', res.name.project.id), ('cancelled_contract_po', '=', res.name.id), ('state', 'not in', ('rejected','cancel','failed'))], limit=1)
                if doc_file:
                    res.write({'penalty_doc': doc_file.id,
                               'penalty_doc_exist': True})
                else:
                    res.write({'penalty_doc': False,
                               'penalty_doc_exist': False})
            else:
                res.write({'penalty_doc': False,
                           'penalty_doc_exist': False})

    def action_cancel(self):
        return{
            'name': 'Cancel Contract',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancel.contract.subcon.variation.order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_contract_subcon': self.id
            }
        }

    def create_bill(self):
        penalty_fee = 0

        if self.method == 'percentage':
            penalty_fee = self.contract_amount_subcon * (self.amount / 100)
        elif self.method == 'fixed':
            penalty_fee = self.amount

        if not self.name.project.penalty_payable:
            raise ValidationError("Set account for penalty payable first.")
        else:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.name.partner_id.id,
                'project_id': self.name.project.id,
                'cancelled_contract_po': self.name.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                'branch_id': self.name.project.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.name.project.penalty_payable.id,
                    'name': 'Penalty fee from contractor',
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                    'analytic_tag_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                    'tax_ids': [(6, 0, [v.id for v in self.tax_id])],
                })],
            })

            return {
                'name': _('Bill Contractor'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': bill.id,
                'res_model': 'account.move',
                'target':'current',
            }

    def create_invoice(self):
        penalty_fee = 0

        if self.diff_penalty == True:
            if self.method_client == 'percentage':
                penalty_fee = self.contract_amount_subcon * (self.amount_client / 100)
            elif self.method_client == 'fixed':
                penalty_fee = self.amount_client
        else:
            if self.method == 'percentage':
                penalty_fee = self.contract_amount * (self.amount / 100)
            elif self.method == 'fixed':
                penalty_fee = self.amount

        if not self.name.project.penalty_receivable:
            raise ValidationError("Set account for penalty receivable first.")
        else:
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'penalty_invoice': True,
                'project_invoice': True,
                'partner_id': self.name.partner_id.id,
                'project_id': self.name.project.id,
                'cancelled_contract_po': self.name.id,
                'invoice_date': datetime.today(),
                'analytic_group_ids': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                'branch_id': self.name.project.branch_id.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': self.name.project.penalty_receivable.id,
                    'name': 'Penalty fee from vendor/subcon',
                    'analytic_account_id': [(6, 0, [v.id for v in self.name.analytic_account_group_ids])],
                    'price_unit': penalty_fee,
                    'price_subtotal': penalty_fee,
                    'tax_ids': [(6, 0, [v.id for v in self.tax_id])],
                })],
            })

            return {
                'name': _('Invoice Vendor/Subcon'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'target':'current',
            }


