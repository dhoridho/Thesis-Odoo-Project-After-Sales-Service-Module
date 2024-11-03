# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, Warning
from lxml import etree

class HrSplitBankTransfer(models.Model):
    _name = "hr.split.bank.transfer"
    _description = "HR Split Bank Transfer"

    @api.returns('self')
    def _get_default_employee(self):
        emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid),('company_id','=',self.company_id.id)], limit=1)
        return emp.id or False
    
    @api.model
    def _get_employee_domain(self):
        domain = [('company_id','=',self.env.company.id)]
        return domain

    number = fields.Char(string="Reference")
    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, default=_get_default_employee,domain=_get_employee_domain)
    payslip_period_id = fields.Many2one('hr.payslip.period', string="Payslip Period", domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]", required=True)
    date_start = fields.Date(string='Date Start', readonly=True, required=True)
    date_end = fields.Date(string='Date End', readonly=True, required=True)
    amount_to_split = fields.Float(string="Amount to Split", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    split_bank_transfer_ids = fields.One2many('hr.split.bank.transfer.details','split_id', string="Split")
    total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_get_total_amount')
    split_approval_line_ids = fields.One2many('hr.split.bank.transfer.approval','split_id', string="Approval Matrix Lines")
    approvers_ids = fields.Many2many('res.users', 'hr_sbt_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', 'hr_sbt_approved_user_rel', string='Approved by User')
    next_approver_ids = fields.Many2many('res.users', 'hr_sbt_next_approver_users_rel', string='Next Approvers', compute="_compute_next_approver", store=True)
    is_next_approvers = fields.Boolean(string="is Next Approvers", compute='_get_is_next_approvers')
    is_sbt_approval_matrix = fields.Boolean("Is SBT Approval Matrix", compute='_compute_is_sbt_approval_matrix')
    is_self_service = fields.Boolean('Self Service', compute='_compute_is_self_service')
    is_computed = fields.Boolean(string="Is Computed")
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrSplitBankTransfer, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrSplitBankTransfer, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.depends('employee_id')
    def _compute_is_self_service(self):
        for rec in self:
            if self.env.user.has_group('hr_payroll_community.group_hr_payroll_community_user') and not self.env.user.has_group('hr_payroll_community.group_hr_payroll_community_manager'):
                rec.is_self_service = True
            else:
                rec.is_self_service = False

    @api.onchange('payslip_period_id')
    def _onchange_payslip_period_id(self):
        for res in self:
            res.month_id = False
            res.date_start = False
            res.date_end = False

    @api.onchange('month_id')
    def _onchange_month(self):
        for res in self:
            if res.month_id:
                period_line_obj = self.env['hr.payslip.period.line'].search(
                    [('id', '=', res.month_id.id)], limit=1)
                if period_line_obj:
                    res.date_start = period_line_obj.start_date
                    res.date_end = period_line_obj.end_date
                else:
                    res.date_start = False
                    res.date_end = False
    
    @api.onchange('employee_id', 'month_id')
    def onchange_employee(self):
        if (not self.employee_id) or (not self.month_id):
            return
        
        payslip = self.env['hr.payslip'].search([('employee_id','=',self.employee_id.id),('month','=',self.month_id.id),('state','=','done')],limit=1)
        if payslip:
            category_net = payslip.line_ids.filtered(lambda line: line.category_id.code == 'NET')
            amount_net = sum(category_net.mapped("total"))
            self.amount_to_split = round(amount_net, 2)
        else:
            self.amount_to_split = 0

    @api.depends('split_bank_transfer_ids.amount')
    def _get_total_amount(self):
        for rec in self:
            total_amount = 0.0
            for line in rec.split_bank_transfer_ids:
                total_amount += line.amount
            rec.update({
                'total_amount': total_amount,
            })

    def compute_amount(self):
        for rec in self:
            for line in rec.split_bank_transfer_ids:
                if line.method == "percentage":
                    if line.percentage <= 0:
                        raise Warning("Please set percentage value.")
                    line.amount = (rec.amount_to_split * line.percentage)/100
            rec.update({
                'is_computed': True
            })
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            hr_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
            if hr_setting.split_bank_transfer_approval_matrix:
                sbt_approval_method = hr_setting.sbt_approval_method
                if record.split_approval_line_ids:
                    remove = []
                    for line in record.split_approval_line_ids:
                        remove.append((2, line.id))
                    record.split_approval_line_ids = remove
                if sbt_approval_method == 'employee_hierarchy':
                    record.split_approval_line_ids = self.approval_by_hierarchy(record)
                    self.app_list_sbt_emp_by_hierarchy()
                else:
                    self.approval_by_matrix(record)
    
    def _compute_is_sbt_approval_matrix(self):
        for rec in self:
            hr_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
            if hr_setting.split_bank_transfer_approval_matrix:
                rec.is_sbt_approval_matrix = True
            else:
                rec.is_sbt_approval_matrix = False
    
    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.employee_id,data,approval_ids,seq)
        return line

    def get_manager(self, record, employee_manager, data, approval_ids, seq):
        hr_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
        if not hr_setting.sbt_approval_levels:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(hr_setting.sbt_approval_levels):
            approval_ids.append(
                (0, 0, {'sequence': seq, 'approver_ids': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(record, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids
    
    def app_list_sbt_emp_by_hierarchy(self):
        for rec in self:
            app_list = []
            for line in rec.split_approval_line_ids:
                app_list.append(line.approver_ids.id)
            rec.approvers_ids = app_list
    
    def approval_by_matrix(self, record):
        app_list = []
        approval_matrix = self.env['hr.sbt.approval.matrix'].search([('apply_to','=','by_employee')])
        matrix = approval_matrix.filtered(lambda line: record.employee_id.id in line.employee_ids.ids)

        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                  'approver_ids': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'approver_ids': [(4, approver)]}))
                        app_list.append(approver)
            record.approvers_ids = app_list
            record.split_approval_line_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.sbt.approval.matrix'].search([('apply_to','=','by_job_position')])
            matrix = approval_matrix.filtered(lambda line: record.employee_id.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                      'approver_ids': [(6, 0, line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                            app_list.append(approver)
                record.approvers_ids = app_list
                record.split_approval_line_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.sbt.approval.matrix'].search([('apply_to','=','by_department')])
                matrix = approval_matrix.filtered(lambda line: record.employee_id.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0,
                                                   {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                    'approver_ids': [(6, 0, line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                                app_list.append(approver)
                    record.approvers_ids = app_list
                    record.split_approval_line_ids = data_approvers
    
    def get_manager_hierarchy(self, record, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(record, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    @api.depends('split_approval_line_ids','split_approval_line_ids.approver_ids','split_approval_line_ids.approver_confirm_ids')
    def _compute_next_approver(self):
        for record in self:
            if record.split_approval_line_ids:
                sequence = [data.sequence for data in record.split_approval_line_ids.filtered(
                    lambda line: len(line.approver_confirm_ids.ids) != line.minimum_approver)]
                if sequence:
                    minimum_sequence = min(sequence)
                    approve_user = record.split_approval_line_ids.filtered(lambda line: line.sequence == minimum_sequence)

                    if approve_user:
                        next_approver = []
                        for approver in approve_user:
                            for rec in approver.approver_ids:
                                if rec.id not in approver.approver_confirm_ids.ids:
                                    next_approver.append(rec.id)
                        record.next_approver_ids = next_approver
                    else:
                        record.next_approver_ids = False
                else:
                    record.next_approver_ids = False
            else:
                record.next_approver_ids = False
    
    @api.depends('next_approver_ids')
    def _get_is_next_approvers(self):
        for rec in self:
            if self.env.user.id in rec.next_approver_ids.ids:
                rec.is_next_approvers = True
            else:
                rec.is_next_approvers = False
    
    @api.constrains('split_bank_transfer_ids')
    def _check_bank_account(self):
        for rec in self:
            exist_bank = []
            for line in rec.split_bank_transfer_ids:
                if line.bank_id.id in exist_bank:
                    raise ValidationError("Please set different Bank Account. Bank Account should be one per line.")
                exist_bank.append(line.bank_id.id)
    
    def submit(self):
        for rec in self:
            method_line = rec.split_bank_transfer_ids.mapped('method')
            if 'percentage' in method_line and not rec.is_computed:
                raise Warning("Please Compute first!")
            
            if round(rec.total_amount, 2) > round(rec.amount_to_split, 2):
                raise ValidationError("Total amount is bigger than the Amount to Split. Please adjust the transaction!")
            
            number = rec.number or self.env['ir.sequence'].next_by_code('hr.split.bank.transfer')
            
            hr_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
            if hr_setting.split_bank_transfer_approval_matrix:
                rec.write({'number': number, 'state': 'submitted'})
                for line in rec.split_bank_transfer_ids:
                    line.write({'state': 'submitted'})
                for approver_line in rec.split_approval_line_ids:
                    approver_line.write({'approver_state': 'draft'})
            else:
                rec.write({'number': number,'state': 'approved'})
                for line in rec.split_bank_transfer_ids:
                    line.write({'state': 'approved'})


    def action_submit(self):
        for rec in self:
            if round(rec.total_amount, 2) < round(rec.amount_to_split, 2):
                res = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.split.bank.transfer.submit.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name':"Confirmation Message",
                    'target': 'new',
                    'context':{'default_split_id':rec.id},
                }
            else:
                res = rec.submit()
            return res
    
    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})
            for line in rec.split_bank_transfer_ids:
                line.write({'state': 'cancelled'})
    
    def action_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.split.bank.transfer.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_split_id':self.id,'default_state':'approved'},
        }
    
    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.split.bank.transfer.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_split_id':self.id,'default_state':'rejected'},
        }
    
    def unlink(self):
        if any(self.filtered(lambda split: split.state not in ('draft','cancelled'))):
            raise UserError(_('You cannot delete a Split Bank Transfer which is not draft or cancelled!'))
        return super(HrSplitBankTransfer, self).unlink()

class HrSplitBankTransferDetails(models.Model):
    _name = "hr.split.bank.transfer.details"
    _description = "HR Split Bank Transfer Details"

    split_id = fields.Many2one('hr.split.bank.transfer', string="Split Bank Transfer", ondelete='cascade')
    employee_id = fields.Many2one(related='split_id.employee_id', string="Employee")
    bank_id = fields.Many2one('bank.account', string="Bank", domain="[('employee_id','=',employee_id)]", ondelete="set null")
    name_of_bank_id = fields.Many2one('res.bank',string="Name Of Bank")
    bank_unit = fields.Char(string="KCP / Unit")
    acc_number = fields.Char(string="Account Number")
    acc_holder = fields.Char(string="Holder Name")
    method = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix_amount', 'Fix Amount'),
    ], string='Method', required=True)
    percentage = fields.Float(string="Percentage(%)")
    amount = fields.Float(string="Amount", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    @api.onchange('bank_id')
    def onchange_bank_id(self):
        for rec in self:
            if rec.bank_id:
                rec.name_of_bank_id = rec.bank_id.name
                rec.bank_unit = rec.bank_id.bank_unit
                rec.acc_number = rec.bank_id.acc_number
                rec.acc_holder = rec.bank_id.acc_holder

    @api.onchange('method')
    def onchange_method(self):
        for rec in self:
            if rec.method == "fix_amount":
                rec.percentage = 0
            if rec.method == "percentage":
                rec.amount = 0

class HrSplitBankTransferApproval(models.Model):
    _name = "hr.split.bank.transfer.approval"
    _description = "HR Split Bank Transfer Approval"

    split_id = fields.Many2one('hr.split.bank.transfer', string="Split Bank Transfer", ondelete='cascade')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_ids = fields.Many2many('res.users', string="Approvers")
    approver_confirm_ids = fields.Many2many('res.users', 'hr_sbt_line_user_approve_rel', 'user_id', string="Approvers confirm")
    approval_status = fields.Text('Approval Status')
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='split_id.state')

    @api.depends('split_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.split_id.split_approval_line_ids:
            sl = sl + 1
            line.sequence = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.approver_ids) < rec.minimum_approver and rec.split_id.state == 'draft':
                rec.minimum_approver = len(rec.approver_ids)