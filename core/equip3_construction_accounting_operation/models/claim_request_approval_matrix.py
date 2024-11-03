from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta, date
from pytz import timezone


class ApprovalMatrixClaimRequest(models.Model):
    _name = 'approval.matrix.claim.request'
    _description = "Approval Matrix Claim Request"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    project_id = fields.Many2many('project.project', string='Project')
    project_director = fields.Many2one('res.users', string='Project Director')
    approval_matrix_ids = fields.One2many('approval.matrix.claim.request.line', 'approval_matrix_id', string="Approver Name")
    progressive_bill = fields.Boolean('Progressive Bill')
    set_default = fields.Boolean(string='Set as Default', default=False)
    
    @api.onchange('progressive_bill')
    def _onchange_progressive_bill(self):
        for rec in self:
            if rec.progressive_bill == False:
                return {
                    'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                }
            else:
                return {
                    'domain': {'project_id': [('department_type', 'in', ('project', 'department')), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                }

    
    @api.constrains('approval_matrix_ids')
    def _check_is_approver_matrix_line_ids_exist(self):
        for record in self:
            if not record.approval_matrix_ids:
                raise ValidationError("Can't save claim request approval matrix because there's no approver in approver line!")
    
    @api.constrains('name', 'progressive_bill')
    def _check_existing_record_name(self):
        for record in self:
            name_id = self.env['approval.matrix.claim.request'].search(
                [('name', '=', record.name), ('progressive_bill', '=', record.progressive_bill)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The Approval matrix name already exists, which is the same as the other approval matrix name.\nPlease change the approval name.')    

    @api.constrains('project_id', 'company_id', 'branch_id', 'progressive_bill', 'set_default')
    def _check_existing_record(self):
        for record in self:
            if record.progressive_bill == False:
                approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                              ('branch_id', '=', record.branch_id.id),
                                              ('id', '!=', record.id),
                                              ('set_default', '=', False),
                                              ('progressive_bill', '=', False)], limit=1)
            
                approval_matrix_id_default = self.search([('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id),
                                                ('id', '!=', record.id),
                                                ('set_default', '=', True),
                                                ('progressive_bill', '=', False)], limit=1)
            
            else:
                approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                              ('branch_id', '=', record.branch_id.id),
                                              ('id', '!=', record.id),
                                              ('set_default', '=', False),
                                              ('progressive_bill', '=', True)], limit=1)
            
                approval_matrix_id_default = self.search([('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id),
                                                ('id', '!=', record.id),
                                                ('set_default', '=', True),
                                                ('progressive_bill', '=', True)], limit=1)
                
            if record.set_default == False:
                for matrix in approval_matrix_id:
                    for proj in matrix.project_id:
                        if proj in record.project_id:
                            raise ValidationError("The claim request approval matrix for this project is already exist in branch %s. Please change the project or the branch.\nExisted approval : '%s'." %((approval_matrix_id.branch_id.name),(approval_matrix_id.name)))
            else:
                if approval_matrix_id_default:
                    raise ValidationError("You have set the approval matrix default and only can set one approval matrix default for all projects in branch {}.\nCurrent Default: '{}'.".format(approval_matrix_id_default.branch_id.name, approval_matrix_id_default.name))

    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(ApprovalMatrixClaimRequest, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class ApprovalMatrixClaimRequestLines(models.Model):
    _name = 'approval.matrix.claim.request.line'
    _description = "Approval Matrix Claim Request Lines"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixClaimRequestLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self._context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_id = fields.Many2one('approval.matrix.claim.request', string='Approval Matrix')
    order_id = fields.Many2one('claim.request.line', string="Claim Request")
    order_id_wiz = fields.Many2one('claim.request', string="Claim Request")
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)
    approval_status = fields.Text()
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()

    
    def unlink(self):
        approval = self.approval_matrix_id
        res = super(ApprovalMatrixClaimRequestLines, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixClaimRequestLines, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res

    @api.onchange('sequence2', 'approvers')
    def _onchange_approver(self):
        for rec in self:
            return {'domain': {'approvers': [('id', 'in', rec.env.ref("account.group_account_user").users.ids + rec.env.ref("account.group_account_manager").users.ids)]}}


class ProgressiveClaimInherit(models.Model):
    _inherit = 'progressive.claim'

    
    is_claim_request_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                     compute='_compute_is_customer_approval_matrix')

    @api.depends('partner_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_claim_request_approval_matrix = IrConfigParam.get_param('is_claim_request_approval_matrix')
        for record in self:
            record.is_claim_request_approval_matrix = is_claim_request_approval_matrix
    

class ClaimRequestInherit(models.Model):
    _inherit = 'claim.request.line'

    approving_matrix_sale_id = fields.Many2one('approval.matrix.claim.request', string="Approval Matrix", store=True)
    approved_matrix_ids = fields.One2many('approval.matrix.claim.request.line', 'order_id', store=True,
                                          string="Approved Matrix")
    is_claim_request_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                     compute='_compute_is_customer_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.claim.request.line', string='Claim Request Approval Matrix Line',
                                              store=False)

    approving_matrix_claim_id = fields.Many2one('approval.matrix.claim.request', string="Approval Matrix",
                                               compute='_compute_approving_customer_matrix', store=True)
    claim_request_user_ids = fields.One2many('claim.request.approver.user', 'claim_request_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'claim_request_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User")
    approved_user = fields.Text(string="Approved User")
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')
    
    @api.depends('project_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_claim_request_approval_matrix = IrConfigParam.get_param('is_claim_request_approval_matrix')
        for record in self:
            record.is_claim_request_approval_matrix = is_claim_request_approval_matrix

    @api.depends('project_id','branch_id','company_id','progressive_bill')
    def _compute_approving_customer_matrix(self):
        for record in self:
            record.approving_matrix_claim_id = False
            if record.is_claim_request_approval_matrix:
                if record.progressive_bill == False:
                    approving_matrix_claim_id = self.env['approval.matrix.claim.request'].search([
                                                ('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id), 
                                                ('project_id', 'in', (record.project_id.id)),  
                                                ('progressive_bill', '=', False), 
                                                ('set_default', '=', False)], limit=1)
                
                    approving_matrix_default = self.env['approval.matrix.claim.request'].search([
                                                ('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id), 
                                                ('set_default', '=', True),
                                                ('progressive_bill', '=', False)], limit=1)
                
                else:
                    approving_matrix_claim_id = self.env['approval.matrix.claim.request'].search([
                                                ('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id), 
                                                ('project_id', 'in', (record.project_id.id)),  
                                                ('progressive_bill', '=', True), 
                                                ('set_default', '=', False)], limit=1)
                    
                    approving_matrix_default = self.env['approval.matrix.claim.request'].search([
                                                ('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id), 
                                                ('set_default', '=', True),
                                                ('progressive_bill', '=', True)], limit=1)
                    
    
                if approving_matrix_claim_id:
                    record.approving_matrix_claim_id = approving_matrix_claim_id and approving_matrix_claim_id.id or False
                else:
                    if approving_matrix_default:
                        record.approving_matrix_claim_id = approving_matrix_default and approving_matrix_default.id or False
    
    @api.onchange('project_id', 'approving_matrix_claim_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.is_claim_request_approval_matrix:
                    record.claim_request_user_ids = []
                    for rec in record.approving_matrix_claim_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.claim_request_user_ids = data


    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.claim_request_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.claim_request_user_ids)
                if app < a:
                    for line in record.claim_request_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False
            
    def action_request_for_approving_matrix(self):
        for record in self:
            action_id = self.env.ref('equip3_construction_accounting_operation.claim_request_action')
            template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval_original')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=claim.request.line'
            if record.claim_request_user_ids and len(record.claim_request_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.claim_request_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'url' : url,
                        'claim_id' : self.claim_id.name,
                    }
                    template_id.with_context(ctx).send_mail(record.id, force_send=True)
                    # template_id.with_context(ctx).send_mail(record.claim_id.id, force_send=True)
            else:
                approver = record.claim_request_user_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'url' : url,
                    'claim_id' : self.claim_id.name,
                }
                template_id.with_context(ctx).send_mail(record.id, force_send=True)
                # template_id.with_context(ctx).send_mail(record.claim_id.id, force_send=True)
            
            record.write({'employee_id': self.env.user.id})

            for line in record.claim_request_user_ids:
                line.write({'approver_state': 'draft'})

    def action_confirm_approving_matrix(self, is_from_monthly=False):
        if self.progressive_bill == False:
            if self.request_for == 'progress':
                if not self.claim_id.project_id.down_payment_id:
                    raise ValidationError("Set account for down payment receivable first.") 
                if not self.claim_id.project_id.accrued_id:
                    raise ValidationError("Set account for claim request receivable first.")
                if not self.claim_id.project_id.retention_id:
                    raise ValidationError("Set account for retention receivable first.")
                if not self.claim_id.project_id.revenue_id:
                    raise ValidationError("Set account for revenue first.")   
        else:
            if self.request_for == 'progress':
                if not self.claim_id.project_id.down_payment_account:
                    raise ValidationError("Set account for down payment payable first.")
                if not self.claim_id.project_id.accrued_account:
                    raise ValidationError("Set account for claim request payable first.")
                if not self.claim_id.project_id.retention_account:
                    raise ValidationError("Set account for retention payable first.")
                if not self.claim_id.project_id.cost_account:
                    raise ValidationError("Set account for cost of revenue first.")
                
        sequence_matrix = [data.name for data in self.claim_request_user_ids]
        sequence_approval = [data.name for data in self.claim_request_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.claim_request_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        
        for record in self:
            action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
            action_id_2 = self.env.ref('equip3_construction_accounting_operation.claim_request_action')
            template_app = self.env.ref('equip3_construction_accounting_operation.email_template_claim_request_approval_approved')
            template_app_2 = self.env.ref('equip3_construction_accounting_operation.email_template_claim_request_approval_approved_original')
            template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval_second')
            template_id_2 = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval_second_original')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
            url_2 = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id_2.id) + '&view_type=form&model=claim.request.line'
            user = self.env.user
            
            current_user = self.env.uid
            if self.env.user.name == 'System Notification':
                now = datetime.now(timezone(record.claim_request_user_ids.user_ids[0].tz))
            else:
                now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            
            if self.env.user not in record.approved_user_ids:
                if record.is_approver or self.env.user.name == 'System Notification':
                    for line in record.claim_request_user_ids:
                        for user in line.user_ids:
                            if self.env.user.name == 'System Notification':
                                line.timestamp = fields.Datetime.now()
                                record.approved_user_ids = [(4, current_user)]
                                var = len(line.approved_employee_ids) + 1
                                if line.minimum_approver <= var:
                                    line.approver_state = 'approved'
                                    string_approval = []
                                    string_approval.append(line.approval_status)
                                    if line.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        line.approval_status = "\n".join(string_approval)
                                        string_timestammp = [line.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        line.approved_time = "\n".join(string_timestammp)
                                    else:
                                        line.approval_status = f"{self.env.user.name}:Approved"
                                        line.approved_time = f"{self.env.user.name}:{dateformat}"
                                    line.is_approve = True
                                else:
                                    line.approver_state = 'pending'
                                    string_approval = []
                                    string_approval.append(line.approval_status)
                                    if line.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        line.approval_status = "\n".join(string_approval)
                                        string_timestammp = [line.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        line.approved_time = "\n".join(string_timestammp)
                                    else:
                                        line.approval_status = f"{self.env.user.name}:Approved"
                                        line.approved_time = f"{self.env.user.name}:{dateformat}"
                                line.approved_employee_ids = [(4, current_user)]
                            elif current_user == user.user_ids.id:
                                line.timestamp = fields.Datetime.now()
                                record.approved_user_ids = [(4, current_user)]
                                var = len(line.approved_employee_ids) + 1
                                if line.minimum_approver <= var:
                                    line.approver_state = 'approved'
                                    string_approval = []
                                    string_approval.append(line.approval_status)
                                    if line.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        line.approval_status = "\n".join(string_approval)
                                        string_timestammp = [line.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        line.approved_time = "\n".join(string_timestammp)
                                    else:
                                        line.approval_status = f"{self.env.user.name}:Approved"
                                        line.approved_time = f"{self.env.user.name}:{dateformat}"
                                    line.is_approve = True
                                else:
                                    line.approver_state = 'pending'
                                    string_approval = []
                                    string_approval.append(line.approval_status)
                                    if line.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        line.approval_status = "\n".join(string_approval)
                                        string_timestammp = [line.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        line.approved_time = "\n".join(string_timestammp)
                                    else:
                                        line.approval_status = f"{self.env.user.name}:Approved"
                                        line.approved_time = f"{self.env.user.name}:{dateformat}"
                                line.approved_employee_ids = [(4, current_user)]

                    matrix_line = sorted(record.claim_request_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : record.employee_id.email,
                                'date': date.today(),
                                'url' : url,
                                'url_2' : url_2,
                                'code' : record.name,
                                'claim_id' : record.claim_id.name,
                                'request' : record.employee_id.name,
                            }
                        template_app.sudo().with_context(ctx).send_mail(record.claim_id.id, True)
                        template_app_2.sudo().with_context(ctx).send_mail(record.id, True)
                        record.write({'state': 'approved',
                                      'approved_progress' : record.requested_progress})
                        
                        if record.claim_id.progressive_bill is False:
                            
                            debit_account_1 = record.project_id.accrued_id.id
                            debit_account_2 = record.project_id.down_payment_id.id
                            debit_account_3 = record.project_id.retention_id.id
                            debit_account_4 = record.project_id.cost_account.id
                            credit_account = record.project_id.revenue_id.id
                            credit_account_2 = record.project_id.cip_account_id.id
                            
                            sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
                            sequence_pool = self.env['ir.sequence']

                            # create journal entry on account.move
                            account_journal_entry = self.env['account.move'].create({
                                'name': sequence_pool.sudo().get_id(sequence_id.id),
                                'journal_claim_id': record.claim_id.id,
                                'project_id': record.project_id.id,
                                'contract_parent': record.contract_parent.id,
                                'request_id': record.id,
                                'analytic_group_ids': record.claim_id.analytic_idz.ids,
                                'journal_id': record.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
                                'ref': 'Claim Request - ' + record.request_id.name,
                                'date': datetime.now(),
                            })

                            accrued_amount = abs(record.account_1)
                            unearned_amount = abs(record.account_2)
                            retention_amount = abs(record.account_3)
                            credit_amount = abs(record.account_4)

                            cip_account_move = record.env['account.move'].search([('analytic_group_ids', 'in', record.claim_id.analytic_idz.ids),('state', '=', 'posted')])
                            cip_debit_amount = 0
                            cip_credit_amount = 0
                            for cip_account in cip_account_move:
                                for line in cip_account.line_ids:
                                    if line.debit > 0 and line.account_id.name == "Construction In Progress":
                                        cip_debit_amount += line.debit
                                    elif line.credit > 0 and line.account_id.name == "Construction In Progress":
                                        cip_credit_amount += line.credit

                            cost_in_progress_amount = cip_debit_amount - cip_credit_amount
                            cost_amount = cost_in_progress_amount

                            journal_items = []
                            for i in range(6):
                                # 0 = credit, 1 = debit 1 (accrued), 2 = debit 2 (unearned), 3 = debit 3 (retention)
                                if i == 0:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'name': 'Claim Request - ' + record.request_id.name,
                                        'account_id': credit_account,
                                        'analytic_tag_ids': record.claim_id.analytic_idz.ids,
                                        'amount_currency': -credit_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': credit_amount,
                                    }))
                                elif i == 1:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'name': 'Claim Request - ' + record.request_id.name,
                                        'account_id': debit_account_1,
                                        'analytic_tag_ids': record.claim_id.analytic_idz.ids,
                                        'amount_currency': accrued_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': accrued_amount,
                                        'credit': 0.0,
                                    }))
                                elif i == 2:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'name': 'Claim Request - ' + record.request_id.name,
                                        'account_id': debit_account_2,
                                        'analytic_tag_ids': record.claim_id.analytic_idz.ids,
                                        'amount_currency': unearned_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': unearned_amount,
                                        'credit': 0.0,
                                    }))
                                elif i == 3:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'name': 'Claim Request - ' + record.request_id.name,
                                        'account_id': debit_account_3,
                                        'analytic_tag_ids': record.claim_id.analytic_idz.ids,
                                        'amount_currency': retention_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': retention_amount,
                                        'credit': 0.0,
                                    }))
                                elif i == 4:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'name': 'Claim Request - ' + record.request_id.name,
                                        'account_id': debit_account_4,
                                        'analytic_tag_ids': record.claim_id.analytic_idz.ids,
                                        'amount_currency': cost_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': cost_amount,
                                        'credit': 0.0,
                                    }))
                                elif i == 5:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'name': 'Claim Request - ' + record.request_id.name,
                                        'account_id': credit_account_2,
                                        'analytic_tag_ids': record.claim_id.analytic_idz.ids,
                                        'amount_currency': -cost_in_progress_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': cost_in_progress_amount,
                                    }))
                            
                            account_journal_entry.line_ids = journal_items

                            # create journal entry on project.journal.entry object on progressive claim
                            claim_journal_entry = self.env['project.journal.entry'].create({
                                'name': account_journal_entry.name,
                                'journal_claim_id': record.claim_id.id,
                                'project_id': record.project_id.id,
                                'contract_parent': record.contract_parent.id,
                                'company_id': record.claim_id.company_id.id,
                                'branch_id': record.claim_id.branch_id.id,
                                'request_id': record.id,
                                'analytic_group_ids': record.claim_id.analytic_idz.ids,
                                'journal_id': account_journal_entry.journal_id.id,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'ref': 'Claim Request - ' + record.request_id.name,
                                'date': datetime.now(),
                                'period_id': account_journal_entry.period_id.id,
                                'fiscal_year': account_journal_entry.fiscal_year.id,
                            })

                            # credit line
                            claim_journal_entry.line_ids.create({
                                'journal_entry_id': claim_journal_entry.id,
                                'account_id': credit_account,
                                'name': claim_journal_entry.ref,
                                'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                'amount_currency': -credit_amount,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'debit': 0.0,
                                'credit': credit_amount,
                            })

                            # credit line
                            claim_journal_entry.line_ids.create({
                                'journal_entry_id': claim_journal_entry.id,
                                'account_id': credit_account_2,
                                'name': claim_journal_entry.ref,
                                'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                'amount_currency': -cost_in_progress_amount,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'debit': 0.0,
                                'credit': cost_in_progress_amount,
                            })

                            # debit line 1 (accrued)
                            claim_journal_entry.line_ids.create({
                                'journal_entry_id': claim_journal_entry.id,
                                'account_id': debit_account_1,
                                'name': claim_journal_entry.ref,
                                'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                'amount_currency': accrued_amount,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'debit': accrued_amount,
                                'credit': 0.0,
                            })

                            # debit line 2 (unearned)
                            claim_journal_entry.line_ids.create({
                                'journal_entry_id': claim_journal_entry.id,
                                'account_id': debit_account_2,
                                'name': claim_journal_entry.ref,
                                'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                'amount_currency': unearned_amount,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'debit': unearned_amount,
                                'credit': 0.0,
                            })

                            # debit line 3 (retention)
                            claim_journal_entry.line_ids.create({
                                'journal_entry_id': claim_journal_entry.id,
                                'account_id': debit_account_3,
                                'name': claim_journal_entry.ref,
                                'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                'amount_currency': retention_amount,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'debit': retention_amount,
                                'credit': 0.0,
                            })

                            # debit line 4 (cost)
                            claim_journal_entry.line_ids.create({
                                'journal_entry_id': claim_journal_entry.id,
                                'account_id': debit_account_4,
                                'name': claim_journal_entry.ref,
                                'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                'amount_currency': cost_amount,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'debit': cost_amount,
                                'credit': 0.0,
                            })

                        elif record.claim_id.progressive_bill is True:
                            # cost_of_revenue_amount = abs(self.max_claim)
                            # advance_amount = cost_of_revenue_amount * (self.claim_id.down_payment / 100)
                            # contract_liabilities_amount = cost_of_revenue_amount - advance_amount

                            cost_of_revenue_amount = abs(record.account_4)
                            advance_amount = abs(record.account_2)
                            retention_amount = abs(record.account_3)
                            contract_liabilities_amount = abs(record.account_1)

                            debit_account = self.claim_id.project_id.cip_account_id.id if self.claim_id.project_id.cip_account_id else self.claim_id.project_id.cost_account.id
                            credit_account_1 = record.claim_id.project_id.down_payment_account.id
                            credit_account_2 = record.claim_id.project_id.accrued_account.id 
                            credit_account_3 = record.claim_id.project_id.retention_account.id

                            sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
                            sequence_pool = self.env['ir.sequence']

                            # create journal entry on account.move object
                            account_journal_entry = self.env['account.move'].create({
                                'name': sequence_pool.sudo().get_id(sequence_id.id),
                                'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
                                'project_id': record.project_id.id,
                                'contract_parent': record.contract_parent.id,
                                'contract_parent_po': record.contract_parent_po.id,
                                'request_id': record.id,
                                'analytic_group_ids': record.claim_id.analytic_idz.ids,
                                'journal_claim_id': record.claim_id.id,
                                'ref': 'Claim Request - ' + record.request_id.name,
                                'date': datetime.now(),
                            })

                            journal_items = []
                            for i in range(4):
                                # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities), 3 = credit (retention)
                                if i == 0:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'account_id': debit_account,
                                        'name': account_journal_entry.ref,
                                        'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': cost_of_revenue_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': cost_of_revenue_amount,
                                        'credit': 0.0,
                                    }))
                                elif i == 1:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'account_id': credit_account_1,
                                        'name': account_journal_entry.ref,
                                        'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': -advance_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': advance_amount,
                                    }))
                                elif i == 2:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'account_id': credit_account_2,
                                        'name': account_journal_entry.ref,
                                        'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': -contract_liabilities_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': contract_liabilities_amount,
                                    }))
                                elif i == 3:
                                    journal_items.append((0, 0, {
                                        'move_id': account_journal_entry.id,
                                        'account_id': credit_account_3,
                                        'name': account_journal_entry.ref,
                                        'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': -retention_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': retention_amount,
                                    }))
                            
                            account_journal_entry.line_ids = journal_items

                            # create journal entry on project.journal.entry object on progressive claim

                            claim_journal_entry = self.env['project.journal.entry'].create({
                                'name': account_journal_entry.name,
                                'journal_claim_id': record.claim_id.id,
                                'project_id': record.project_id.id,
                                'contract_parent': record.contract_parent.id,
                                'contract_parent_po': record.contract_parent_po.id,
                                'company_id': record.claim_id.company_id.id,
                                'branch_id': record.claim_id.branch_id.id,
                                'request_id': record.id,
                                'analytic_group_ids': record.claim_id.analytic_idz.ids,
                                'journal_id': account_journal_entry.journal_id.id,
                                'currency_id': record.claim_id.company_currency_id.id,
                                'ref': 'Claim Request - ' + record.request_id.name,
                                'date': datetime.now(),
                                'period_id': account_journal_entry.period_id.id,
                                'fiscal_year': account_journal_entry.fiscal_year.id,
                            })

                            claim_journal_items = []
                            for i in range(4):
                                # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities)
                                if i == 0:
                                    claim_journal_items.append((0, 0, {
                                        'journal_entry_id': claim_journal_entry.id,
                                        'account_id': debit_account,
                                        'name': claim_journal_entry.ref,
                                        'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': cost_of_revenue_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': cost_of_revenue_amount,
                                        'credit': 0.0,
                                    }))
                                elif i == 1:
                                    claim_journal_items.append((0, 0, {
                                        'journal_entry_id': claim_journal_entry.id,
                                        'account_id': credit_account_1,
                                        'name': claim_journal_entry.ref,
                                        'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': -advance_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': advance_amount,
                                    }))
                                elif i == 2:
                                    claim_journal_items.append((0, 0, {
                                        'journal_entry_id': claim_journal_entry.id,
                                        'account_id': credit_account_2,
                                        'name': claim_journal_entry.ref,
                                        'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': -contract_liabilities_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': contract_liabilities_amount,
                                    }))
                                elif i == 3:
                                    claim_journal_items.append((0, 0, {
                                        'journal_entry_id': claim_journal_entry.id,
                                        'account_id': credit_account_3,
                                        'name': claim_journal_entry.ref,
                                        'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                                        'amount_currency': -retention_amount,
                                        'currency_id': record.claim_id.company_currency_id.id,
                                        'debit': 0.0,
                                        'credit': retention_amount,
                                    }))

                            claim_journal_entry.line_ids = claim_journal_items
                        
                    else:
                        record.last_approved = self.env.user.id
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        for approving_matrix_line_user in matrix_line[0].user_ids:
                            ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : approving_matrix_line_user.partner_id.email,
                                'approver_name' : approving_matrix_line_user.name,
                                'date': date.today(),
                                'submitter' : record.last_approved.name,
                                'url' : url,
                                'url_2' : url_2,
                                'code' : record.name,
                                'claim_id' : record.claim_id.name,
                            }
                            template_id.sudo().with_context(ctx).send_mail(record.claim_id.id, True)
                            template_id_2.sudo().with_context(ctx).send_mail(record.id, True)
                        
                else:
                    raise ValidationError(_(
                        'You are not allowed to perform this action!'
                    ))
            else:
                raise ValidationError(_(
                    'Already approved!'
                ))
            
        claim_id = self.claim_id.id
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
        action['res_id'] = claim_id
        if not is_from_monthly:
            return action

    def action_reject_approval(self):
        for record in self:
            action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
            action_id_2 = self.env.ref('equip3_construction_accounting_operation.claim_request_action')
            template_rej = self.env.ref('equip3_construction_accounting_operation.email_template_claim_request_approval_rejected')
            template_rej_2 = self.env.ref('equip3_construction_accounting_operation.email_template_claim_request_approval_rejected_original')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
            url_2 = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id_2.id) + '&view_type=form&model=claim.request.line'
            for user in record.claim_request_user_ids:
                for check_user in user.user_ids:
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                    if self.env.uid == check_user.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'reject'
                        string_approval = []
                        string_approval.append(user.approval_status)
                        if user.approval_status:
                            string_approval.append(f"{self.env.user.name}:Rejected")
                            user.approval_status = "\n".join(string_approval)
                            string_timestammp = [user.approved_time]
                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                            user.approved_time = "\n".join(string_timestammp)
                        else:
                            user.approval_status = f"{self.env.user.name}:Rejected"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"
            
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.employee_id.email,
                    'date': date.today(),
                    'url' : url,
                    'url_2' : url_2,
                    'code' : record.name,
                    'claim_id' : record.claim_id.name,
                    'request' : record.employee_id.name,
                }
            template_rej.sudo().with_context(ctx).send_mail(record.claim_id.id, True)
            template_rej_2.sudo().with_context(ctx).send_mail(record.id, True)
            
            record.write({'state': 'rejected',
                          'requested_progress_2': 0
                        })
            if record.request_ids:
                for res in record.request_ids:
                    res.write({'wo_prog_temp': 0})
        
    
    def action_reject_approving_matrix(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.claim.request.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            "context": {'default_claim_id': self.claim_id and self.claim_id.id or False}
        }


    # @api.depends('approving_matrix_sale_id')
    # def _compute_approval_matrix_filled(self):
    #     for record in self:
    #         record.is_approval_matrix_filled = False
    #         if record.approving_matrix_sale_id:
    #             record.is_approval_matrix_filled = True

    # def _get_approve_button(self):
    #     for record in self:
    #         matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved),
    #                              key=lambda r: r.sequence)
    #         if len(matrix_line) == 0:
    #             record.is_approve_button = False
    #             record.approval_matrix_line_id = False
    #         elif len(matrix_line) > 0:
    #             matrix_line_id = matrix_line[0]
    #             if self.env.user.id in matrix_line_id.user_name_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
    #                 record.is_approve_button = True
    #                 record.approval_matrix_line_id = matrix_line_id.id
    #             else:
    #                 record.is_approve_button = False
    #                 record.approval_matrix_line_id = False
    #         else:
    #             record.is_approve_button = False
    #             record.approval_matrix_line_id = False
                

    # @api.depends('project_id')
    # def _compute_is_customer_approval_matrix(self):
    #     IrConfigParam = self.env['ir.config_parameter'].sudo()
    #     is_claim_request_approval_matrix = IrConfigParam.get_param('is_claim_request_approval_matrix')
    #     for record in self:
    #         record.is_claim_request_approval_matrix = is_claim_request_approval_matrix
    
    # @api.onchange('project_id')
    # def onchange_partner_id_new(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.onchange('request_id')
    # def _onchange_sale_name(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()
    
    # @api.onchange('partner_id')
    # def _onchange_partner(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()
    
    # @api.onchange('vendor')
    # def _onchange_vendor(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.depends('approving_matrix_sale_id')
    # def _compute_approving_matrix_lines(self):
    #     data = [(5, 0, 0)]
    #     for record in self:
    #         if record.state == 'to_approve' and record.is_claim_request_approval_matrix:
    #             record.approved_matrix_ids = []
    #             counter = 1
    #             record.approved_matrix_ids = []
    #             for rec in record.approving_matrix_sale_id:
    #                 for line in rec.approver_matrix_line_ids:
    #                     data.append((0, 0, {
    #                         'sequence': counter,
    #                         'user_name_ids': [(6, 0, line.user_name_ids.ids)],
    #                         'minimum_approver': line.minimum_approver,
    #                     }))
    #                     counter += 1
    #             record.approved_matrix_ids = data

    # @api.depends('project_id','branch_id','company_id','progressive_bill')
    # def _compute_approving_customer_matrix(self):
    #     for record in self:
    #         record.approving_matrix_sale_id = False
    #         if record.is_claim_request_approval_matrix:
    #             if record.progressive_bill == False:
    #                 approving_matrix_sale_id = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('project_id', 'in', (record.project_id.id)),  
    #                                             ('progressive_bill', '=', False), 
    #                                             ('set_default', '=', False)], limit=1)
                
    #                 approving_matrix_default = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('set_default', '=', True),
    #                                             ('progressive_bill', '=', False)], limit=1)
                
    #             else:
    #                 approving_matrix_sale_id = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('project_id', 'in', (record.project_id.id)),  
    #                                             ('progressive_bill', '=', True), 
    #                                             ('set_default', '=', False)], limit=1)
                    
    #                 approving_matrix_default = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('set_default', '=', True),
    #                                             ('progressive_bill', '=', True)], limit=1)
                    
    
    #             if approving_matrix_sale_id:
    #                 record.approving_matrix_sale_id = approving_matrix_sale_id and approving_matrix_sale_id.id or False
    #             else:
    #                 if approving_matrix_default:
    #                     record.approving_matrix_sale_id = approving_matrix_default and approving_matrix_default.id or False
    

    # def action_confirm_approving_matrix(self):
    #     if self.progressive_bill == False:
    #         if self.request_for == 'progress':
    #             if not self.claim_id.project_id.down_payment_id:
    #                 raise ValidationError("Set account for down payment receivable first.") 
    #             if not self.claim_id.project_id.accrued_id:
    #                 raise ValidationError("Set account for claim request receivable first.")
    #             if not self.claim_id.project_id.retention_id:
    #                 raise ValidationError("Set account for retention receivable first.")
    #             if not self.claim_id.project_id.revenue_id:
    #                 raise ValidationError("Set account for revenue first.")   
    #     else:
    #         if self.request_for == 'progress':
    #             if not self.claim_id.project_id.down_payment_account:
    #                 raise ValidationError("Set account for down payment payable first.")
    #             if not self.claim_id.project_id.accrued_account:
    #                 raise ValidationError("Set account for claim request payable first.")
    #             if not self.claim_id.project_id.retention_account:
    #                 raise ValidationError("Set account for retention payable first.")
    #             if not self.claim_id.project_id.cost_account:
    #                 raise ValidationError("Set account for cost of revenue first.")
                
    #     for record in self:
    #         user = self.env.user
    #         if record.is_approve_button and record.approval_matrix_line_id:
    #             approval_matrix_line_id = record.approval_matrix_line_id
    #             if user.id in approval_matrix_line_id.user_name_ids.ids and \
    #                     user.id not in approval_matrix_line_id.approved_users.ids:
    #                 name = approval_matrix_line_id.state_char or ''
    #                 if name != '':
    #                     name += "\n • %s: Approved" % (self.env.user.name)
    #                 else:
    #                     name += "• %s: Approved" % (self.env.user.name)

    #                 approval_matrix_line_id.write({
    #                     'last_approved': self.env.user.id, 'state_char': name,
    #                     'approved_users': [(4, user.id)]})
    #                 if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
    #                     approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
    #                     next_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved and r.id != approval_matrix_line_id.id),
    #                              key=lambda r: r.sequence)
    #                     submitter = self.env.user
    #                     if len(next_line) > 0:
    #                         template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval')
    #                         action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
    #                         for user in next_line[0].user_name_ids:
    #                             base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #                             url = base_url + '/web#id=' + str(record.claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
    #                             ctx = {
    #                                 'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
    #                                 'email_to' : user.partner_id.email,
    #                                 'approver_name' : user.partner_id.name,
    #                                 'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
    #                                 'url' : url,
    #                                 'cr_name': record.request_id.name,
    #                                 'submitter': submitter.partner_id.name
    #                             }
    #                             template_id.sudo().with_context(ctx).send_mail(record.claim_id.id, True)


    #         if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
    #             record.write({'state': 'approved',
    #                           'approved_progress' : record.requested_progress})
                              
    #     if self.claim_id.progressive_bill == False:
    #         debit_account_1 = self.project_id.accrued_id.id
    #         debit_account_2 = self.project_id.down_payment_id.id
    #         debit_account_3 = self.project_id.retention_id.id
    #         credit_account = self.project_id.revenue_id.id
            
    #         sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
    #         sequence_pool = self.env['ir.sequence']

    #         # create journal entry on account.move
    #         account_journal_entry = self.env['account.move'].create({
    #             'name': sequence_pool.sudo().get_id(sequence_id.id),
    #             'journal_claim_id': self.claim_id.id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #         })

    #         accrued_amount = abs(self.account_1)
    #         unearned_amount = abs(self.account_2)
    #         retention_amount = abs(self.account_3)
    #         credit_amount = abs(self.account_4)

    #         journal_items = []
    #         for i in range(4):
    #             # 0 = credit, 1 = debit 1 (accrued), 2 = debit 2 (unearned), 3 = debit 3 (retention)
    #             if i == 0:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': credit_account,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': -credit_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': credit_amount,
    #                 }))
    #             elif i == 1:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': debit_account_1,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': accrued_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': accrued_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 2:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': debit_account_2,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': unearned_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': unearned_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 3:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': debit_account_3,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': retention_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': retention_amount,
    #                     'credit': 0.0,
    #                 }))
            
    #         account_journal_entry.line_ids = journal_items

    #         # create journal entry on project.journal.entry object on progressive claim
    #         claim_journal_entry = self.env['project.journal.entry'].create({
    #             'name': account_journal_entry.name,
    #             'journal_claim_id': self.claim_id.id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'company_id': self.claim_id.company_id.id,
    #             'branch_id': self.claim_id.branch_id.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_id': account_journal_entry.journal_id.id,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #             'period_id': account_journal_entry.period_id.id,
    #             'fiscal_year': account_journal_entry.fiscal_year.id,
    #         })

    #         # credit line
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': credit_account,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': -credit_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': 0.0,
    #             'credit': credit_amount,
    #         })

    #         # debit line 1 (accrued)
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': debit_account_1,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': accrued_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': accrued_amount,
    #             'credit': 0.0,
    #         })

    #         # debit line 2 (unearned)
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': debit_account_2,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': unearned_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': unearned_amount,
    #             'credit': 0.0,
    #         })

    #         # debit line 3 (retention)
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': debit_account_3,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': retention_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': retention_amount,
    #             'credit': 0.0,
    #         })

    #     elif self.claim_id.progressive_bill == True:
    #         # cost_of_revenue_amount = abs(self.max_claim)
    #         # advance_amount = cost_of_revenue_amount * (self.claim_id.down_payment / 100)
    #         # contract_liabilities_amount = cost_of_revenue_amount - advance_amount

    #         cost_of_revenue_amount = abs(self.account_4)
    #         advance_amount = abs(self.account_2)
    #         retention_amount = abs(self.account_3)
    #         contract_liabilities_amount = abs(self.account_1)

    #         debit_account = self.claim_id.project_id.cost_account.id
    #         credit_account_1 = self.claim_id.project_id.down_payment_account.id
    #         credit_account_2 = self.claim_id.project_id.accrued_account.id 
    #         credit_account_3 = self.claim_id.project_id.retention_account.id

    #         sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
    #         sequence_pool = self.env['ir.sequence']

    #         # create journal entry on account.move object
    #         account_journal_entry = self.env['account.move'].create({
    #             'name': sequence_pool.sudo().get_id(sequence_id.id),
    #             'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'contract_parent_po': self.contract_parent_po.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_claim_id': self.claim_id.id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #         })

    #         journal_items = []
    #         for i in range(4):
    #             # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities), 3 = credit (retention)
    #             if i == 0:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': debit_account,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': cost_of_revenue_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': cost_of_revenue_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 1:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': credit_account_1,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -advance_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': advance_amount,
    #                 }))
    #             elif i == 2:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': credit_account_2,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -contract_liabilities_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': contract_liabilities_amount,
    #                 }))
    #             elif i == 3:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': credit_account_3,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -retention_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': retention_amount,
    #                 }))
            
    #         account_journal_entry.line_ids = journal_items

    #         # create journal entry on project.journal.entry object on progressive claim

    #         claim_journal_entry = self.env['project.journal.entry'].create({
    #             'name': account_journal_entry.name,
    #             'journal_claim_id': self.claim_id.id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'contract_parent_po': self.contract_parent_po.id,
    #             'company_id': self.claim_id.company_id.id,
    #             'branch_id': self.claim_id.branch_id.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_id': account_journal_entry.journal_id.id,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #             'period_id': account_journal_entry.period_id.id,
    #             'fiscal_year': account_journal_entry.fiscal_year.id,
    #         })

    #         claim_journal_items = []
    #         for i in range(4):
    #             # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities)
    #             if i == 0:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': debit_account,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': cost_of_revenue_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': cost_of_revenue_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 1:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': credit_account_1,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -advance_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': advance_amount,
    #                 }))
    #             elif i == 2:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': credit_account_2,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -contract_liabilities_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': contract_liabilities_amount,
    #                 }))
    #             elif i == 3:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': credit_account_3,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -retention_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': retention_amount,
    #                 }))

    #         claim_journal_entry.line_ids = claim_journal_items

    #     claim_id = self.claim_id.id
    #     action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
    #     action['res_id'] = claim_id

    #     return action

    # def action_reject_approving_matrix(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Reject Reason',
    #         'res_model': 'approval.matrix.claim.request.reject',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         "context": {'default_claim_id': self.claim_id and self.claim_id.id or False}
    #     }

    # def action_confirm_approving(self):
    #     if self.progressive_bill == False:
    #         if self.request_for == 'progress':
    #             if not self.claim_id.project_id.down_payment_id:
    #                 raise ValidationError("Set account for down payment receivable first.") 
    #             if not self.claim_id.project_id.accrued_id:
    #                 raise ValidationError("Set account for claim request receivable first.")
    #             if not self.claim_id.project_id.retention_id:
    #                 raise ValidationError("Set account for retention receivable first.")
    #             if not self.claim_id.project_id.revenue_id:
    #                 raise ValidationError("Set account for revenue first.")   
    #     else:
    #         if self.request_for == 'progress':
    #             if not self.claim_id.project_id.down_payment_account:
    #                 raise ValidationError("Set account for down payment payable first.")
    #             if not self.claim_id.project_id.accrued_account:
    #                 raise ValidationError("Set account for claim request payable first.")
    #             if not self.claim_id.project_id.retention_account:
    #                 raise ValidationError("Set account for retention payable first.")
    #             if not self.claim_id.project_id.cost_account:
    #                 raise ValidationError("Set account for cost of revenue first.")
        
    #     if self.claim_id.claim_type == "milestone":
    #         progress_to_invoiced = False
    #         min_ct = 101
    #         approved_progress = self.claim_id.approved_progress + self.requested_progress
    #         for m in self.claim_id.milestone_term_ids:
    #             if m.type_milestone == "progress" and m.is_invoiced == False and m.exist_progress_reminder == False and m.claim_percentage < min_ct and m.claim_percentage <= approved_progress:
    #                 min_ct = m.claim_percentage
    #                 progress_to_invoiced = m
            
    #         if progress_to_invoiced != False:
    #             progress_to_invoiced.write({'exist_progress_reminder': True})
    #             template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_milestone_create_invoice')
    #             if self.claim_id.progressive_bill == False:
    #                 action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
    #             else:
    #                 action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

    #             for user in self.claim_id.project_id.notification_claim:
    #                 base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #                 url = base_url + '/web#id=' + str(self.claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
    #                 ctx = {
    #                     'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
    #                     'email_to' : user.partner_id.email,
    #                     'approver_name' : user.partner_id.name,
    #                     'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
    #                     'url' : url,
    #                     'next_milestone': progress_to_invoiced.name,
    #                     'invoice_for': "Down Payment"
    #                 }
    #                 template_id.sudo().with_context(ctx).send_mail(self.claim_id.id, True)
            

    #     for record in self:
    #         record.write({'state': 'approved',
    #                       'approved_progress' : record.requested_progress})

    #     if self.claim_id.progressive_bill == False:
    #         debit_account_1 = self.project_id.accrued_id.id
    #         debit_account_2 = self.project_id.down_payment_id.id
    #         debit_account_3 = self.project_id.retention_id.id
    #         credit_account = self.project_id.revenue_id.id
            
    #         sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
    #         sequence_pool = self.env['ir.sequence']

    #         # create journal entry on account.move
    #         account_journal_entry = self.env['account.move'].create({
    #             'name': sequence_pool.sudo().get_id(sequence_id.id),
    #             'journal_claim_id': self.claim_id.id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #         })

    #         accrued_amount = abs(self.account_1)
    #         unearned_amount = abs(self.account_2)
    #         retention_amount = abs(self.account_3)
    #         credit_amount = abs(self.account_4)

    #         journal_items = []
    #         for i in range(4):
    #             # 0 = credit, 1 = debit 1 (accrued), 2 = debit 2 (unearned), 3 = debit 3 (retention)
    #             if i == 0:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': credit_account,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': -credit_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': credit_amount,
    #                 }))
    #             elif i == 1:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': debit_account_1,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': accrued_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': accrued_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 2:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': debit_account_2,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': unearned_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': unearned_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 3:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'name': 'Claim Request - ' + self.request_id.name,
    #                     'account_id': debit_account_3,
    #                     'analytic_tag_ids': self.claim_id.analytic_idz.ids,
    #                     'amount_currency': retention_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': retention_amount,
    #                     'credit': 0.0,
    #                 }))
            
    #         account_journal_entry.line_ids = journal_items

    #         # create journal entry on project.journal.entry object on progressive claim
    #         claim_journal_entry = self.env['project.journal.entry'].create({
    #             'name': account_journal_entry.name,
    #             'journal_claim_id': self.claim_id.id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'company_id': self.claim_id.company_id.id,
    #             'branch_id': self.claim_id.branch_id.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_id': account_journal_entry.journal_id.id,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #             'period_id': account_journal_entry.period_id.id,
    #             'fiscal_year': account_journal_entry.fiscal_year.id,
    #         })

    #         # credit line
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': credit_account,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': -credit_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': 0.0,
    #             'credit': credit_amount,
    #         })

    #         # debit line 1 (accrued)
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': debit_account_1,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': accrued_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': accrued_amount,
    #             'credit': 0.0,
    #         })

    #         # debit line 2 (unearned)
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': debit_account_2,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': unearned_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': unearned_amount,
    #             'credit': 0.0,
    #         })

    #         # debit line 3 (retention)
    #         claim_journal_entry.line_ids.create({
    #             'journal_entry_id': claim_journal_entry.id,
    #             'account_id': debit_account_3,
    #             'name': claim_journal_entry.ref,
    #             'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #             'amount_currency': retention_amount,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'debit': retention_amount,
    #             'credit': 0.0,
    #         })

    #     elif self.claim_id.progressive_bill == True:
    #         # cost_of_revenue_amount = abs(self.max_claim)
    #         # advance_amount = cost_of_revenue_amount * (self.claim_id.down_payment / 100)
    #         # contract_liabilities_amount = cost_of_revenue_amount - advance_amount

    #         cost_of_revenue_amount = abs(self.account_4)
    #         advance_amount = abs(self.account_2)
    #         retention_amount = abs(self.account_3)
    #         contract_liabilities_amount = abs(self.account_1)

    #         debit_account = self.claim_id.project_id.cost_account.id
    #         credit_account_1 = self.claim_id.project_id.down_payment_account.id
    #         credit_account_2 = self.claim_id.project_id.accrued_account.id
    #         credit_account_3 = self.claim_id.project_id.retention_account.id

    #         sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
    #         sequence_pool = self.env['ir.sequence']

    #         # create journal entry on account.move object
    #         account_journal_entry = self.env['account.move'].create({
    #             'name': sequence_pool.sudo().get_id(sequence_id.id),
    #             'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'contract_parent_po': self.contract_parent_po.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_claim_id': self.claim_id.id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #         })

    #         journal_items = []
    #         for i in range(4):
    #             # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities), 3 = credit (retention)
    #             if i == 0:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': debit_account,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': cost_of_revenue_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': cost_of_revenue_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 1:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': credit_account_1,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -advance_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': advance_amount,
    #                 }))
    #             elif i == 2:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': credit_account_2,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -contract_liabilities_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': contract_liabilities_amount,
    #                 }))
    #             elif i == 3:
    #                 journal_items.append((0, 0, {
    #                     'move_id': account_journal_entry.id,
    #                     'account_id': credit_account_3,
    #                     'name': account_journal_entry.ref,
    #                     'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -retention_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': retention_amount,
    #                 }))
            
    #         account_journal_entry.line_ids = journal_items

    #         # create journal entry on project.journal.entry object on progressive claim

    #         claim_journal_entry = self.env['project.journal.entry'].create({
    #             'name': account_journal_entry.name,
    #             'journal_claim_id': self.claim_id.id,
    #             'project_id': self.project_id.id,
    #             'contract_parent': self.contract_parent.id,
    #             'contract_parent_po': self.contract_parent_po.id,
    #             'company_id': self.claim_id.company_id.id,
    #             'branch_id': self.claim_id.branch_id.id,
    #             'request_id': self.id,
    #             'analytic_group_ids': self.claim_id.analytic_idz.ids,
    #             'journal_id': account_journal_entry.journal_id.id,
    #             'currency_id': self.claim_id.company_currency_id.id,
    #             'ref': 'Claim Request - ' + self.request_id.name,
    #             'date': datetime.now(),
    #             'period_id': account_journal_entry.period_id.id,
    #             'fiscal_year': account_journal_entry.fiscal_year.id,
    #         })

    #         claim_journal_items = []
    #         for i in range(4):
    #             # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities)
    #             if i == 0:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': debit_account,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': cost_of_revenue_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': cost_of_revenue_amount,
    #                     'credit': 0.0,
    #                 }))
    #             elif i == 1:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': credit_account_1,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -advance_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': advance_amount,
    #                 }))
    #             elif i == 2:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': credit_account_2,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -contract_liabilities_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': contract_liabilities_amount,
    #                 }))
    #             elif i == 3:
    #                 claim_journal_items.append((0, 0, {
    #                     'journal_entry_id': claim_journal_entry.id,
    #                     'account_id': credit_account_3,
    #                     'name': claim_journal_entry.ref,
    #                     'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
    #                     'amount_currency': -retention_amount,
    #                     'currency_id': self.claim_id.company_currency_id.id,
    #                     'debit': 0.0,
    #                     'credit': retention_amount,
    #                 }))

    #         claim_journal_entry.line_ids = claim_journal_items

    #     claim_id = self.claim_id.id
    #     action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
    #     action['res_id'] = claim_id
        
    #     return action

    
class ClaimRequestApproverUser(models.Model):
    _name = 'claim.request.approver.user'

    claim_request_approver_id = fields.Many2one('claim.request.line', string="Claim Request")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'claim_request_app_emp_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('reject', 'Rejected')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'claim_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(related='claim_request_approver_id.state', string='Parent Status')

    @api.depends('claim_request_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.claim_request_approver_id.claim_request_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.claim_request_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.claim_request_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids

