from ast import Store
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
from pytz import timezone


class ProjectBudgetCarry(models.Model):
    _name = 'project.budget.carry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id DESC'
    _description = 'Budget Carry Over'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'budget.carry.over.sequence') or 'New'
        return super(ProjectBudgetCarry, self).create(vals)

    name = fields.Char(string='Number', copy=False, required=True, readonly=True, 
                        index=True, default=lambda self: _('New'))
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id,
                                 readonly=True)
    project_id = fields.Many2one('project.project', string='Project', required=True,
                                 domain="[('primary_states','=', 'progress'), ('budgeting_period','!=', 'project')]")
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)])
    from_project_budget_id = fields.Many2one('project.budget', domain="[('state','in', ['in_progress']), ('project_id','=', project_id)]",
                                             string="From Periodical Budget", required=True, )
    to_project_budget_id = fields.Many2one('project.budget', domain="[('state','=', ['in_progress']), ('project_id','=', project_id)]",
                                           string="To Periodical Budget", required=True, )
    approve_date = fields.Datetime(string="Approved Date", readonly=True)
    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user, readonly=True)
    creation_date = fields.Datetime(string="Creation Date", default=fields.Datetime.now, readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id,
                                  readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'Request For Approval'),
                              ('approve', 'Approved'), ('reject', 'Rejected'), ('done', 'Done')], 
                              string="State", readonly=True, tracking=True, default='draft')
    state1 = fields.Selection(related='state', tracking=False)
    state2 = fields.Selection(related='state', tracking=False)

    budget_carry_material_ids = fields.One2many('material.estimation', 'budget_carry_over_id')
    budget_carry_Labour_ids = fields.One2many('labour.estimation', 'budget_carry_over_id')
    budget_carry_internal_asset_ids = fields.One2many('internal.asset.estimation', 'budget_carry_over_id')
    budget_carry_equipment_ids = fields.One2many('equipment.lease.estimation', 'budget_carry_over_id')
    budget_carry_subcon_ids = fields.One2many('subcon.estimation', 'budget_carry_over_id')
    budget_carry_overhead_ids = fields.One2many('overhead.estimation', 'budget_carry_over_id')
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')

    # approval matrix
    budget_carry_over_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                     compute='is_budget_carry_over_approval_matrix')
    approving_matrix_budget_carry_id = fields.Many2one('approval.matrix.budget.carry.over', string="Approval Matrix",
                                                compute='_compute_approving_customer_matrix', store=True)
    budget_carry_user_ids = fields.One2many('budget.carry.approver.user', 'budget_carry_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'budget_carry_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            
        return super(ProjectBudgetCarry, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            
        return super(ProjectBudgetCarry, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.depends('project_id')
    def is_budget_carry_over_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        budget_carry_over_approval_matrix = IrConfigParam.get_param('budget_carry_over_approval_matrix')
        for record in self:
            record.budget_carry_over_approval_matrix = budget_carry_over_approval_matrix
    
    @api.depends('project_id','branch_id','company_id','department_type')
    def _compute_approving_customer_matrix(self):
        for res in self:
            res.approving_matrix_budget_carry_id = False
            if res.budget_carry_over_approval_matrix:
                if res.department_type == 'project':
                    approving_matrix_budget_carry_id = self.env['approval.matrix.budget.carry.over'].search([
                                                ('company_id', '=', res.company_id.id),
                                                ('branch_id', '=', res.branch_id.id), 
                                                ('project_id', 'in', (res.project_id.id)),  
                                                ('department_type', '=', 'project'), 
                                                ('set_default', '=', False)], limit=1)
                
                    approving_matrix_default = self.env['approval.matrix.budget.carry.over'].search([
                                                ('company_id', '=', res.company_id.id),
                                                ('branch_id', '=', res.branch_id.id), 
                                                ('set_default', '=', True),
                                                ('department_type', '=', 'project')], limit=1)
                
                else:
                    approving_matrix_budget_carry_id = self.env['approval.matrix.budget.carry.over'].search([
                                                ('company_id', '=', res.company_id.id),
                                                ('branch_id', '=', res.branch_id.id), 
                                                ('project_id', 'in', (res.project_id.id)),  
                                                ('department_type', '=', 'department'), 
                                                ('set_default', '=', False)], limit=1)
                    
                    approving_matrix_default = self.env['approval.matrix.budget.carry.over'].search([
                                                ('company_id', '=', res.company_id.id),
                                                ('branch_id', '=', res.branch_id.id), 
                                                ('set_default', '=', True),
                                                ('department_type', '=', 'department')], limit=1)
                    
    
                if approving_matrix_budget_carry_id:
                    res.approving_matrix_budget_carry_id = approving_matrix_budget_carry_id and approving_matrix_budget_carry_id.id or False
                else:
                    if approving_matrix_default:
                        res.approving_matrix_budget_carry_id = approving_matrix_default and approving_matrix_default.id or False
                    else:
                        res.approving_matrix_budget_carry_id = False

    @api.onchange('project_id', 'approving_matrix_budget_carry_id')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.budget_carry_over_approval_matrix:
                    record.budget_carry_user_ids = []
                    for rec in record.approving_matrix_budget_carry_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.budget_carry_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.budget_carry_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.budget_carry_user_ids)
                if app < a:
                    for line in record.budget_carry_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def request_approval(self):
        if len(self.budget_carry_user_ids) == 0:
            raise ValidationError(
                _("There's no budget carry over approval matrix for this project or approval matrix default created. You have to create it first."))
        
        for record in self:
            action_id = self.env.ref('equip3_construction_operation.project_budget_carry_action_id')
            template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_budget_carry_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=project.budget.carry'
            if record.budget_carry_user_ids and len(record.budget_carry_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.budget_carry_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'url' : url,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
            else:
                approver = record.budget_carry_user_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'url' : url,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
            
            record.write({'employee_id': self.env.user.id,
                          'state': 'to_approve',
                          })

            for line in record.budget_carry_user_ids:
                line.write({'approver_state': 'draft'})

    def btn_approve(self):
        sequence_matrix = [data.name for data in self.budget_carry_user_ids]
        sequence_approval = [data.name for data in self.budget_carry_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.budget_carry_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        
        for record in self:
            action_id = self.env.ref('equip3_construction_operation.project_budget_carry_action_id')
            template_app = self.env.ref('equip3_construction_operation.email_template_budget_carry_approved')
            template_id = self.env.ref('equip3_construction_operation.email_template_reminder_for_budget_carry_approval_temp')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=project.budget.carry'
            
            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

            if self.env.user not in record.approved_user_ids:
                if record.is_approver:
                    for line in record.budget_carry_user_ids:
                        for user in line.user_ids:
                            if current_user == user.user_ids.id:
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

                    matrix_line = sorted(record.budget_carry_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : record.employee_id.email,
                                'date': date.today(),
                                'url' : url,
                            }
                        template_app.sudo().with_context(ctx).send_mail(record.id, True)
                        record.write({'state': 'approve'})
                        
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
                            }
                            template_id.sudo().with_context(ctx).send_mail(record.id, True)
                        
                else:
                    raise ValidationError(_(
                        'You are not allowed to perform this action!'
                    ))
            else:
                raise ValidationError(_(
                    'Already approved!'
                ))
        
    def action_reject_approval(self):
        for record in self:
            action_id = self.env.ref('equip3_construction_operation.project_budget_carry_action_id')
            template_rej = self.env.ref('equip3_construction_operation.email_template_budget_carry_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=project.budget.carry'
            for user in record.budget_carry_user_ids:
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
                }
            template_rej.sudo().with_context(ctx).send_mail(record.id, True)
            record.write({'state': 'reject'})

    def set_carry_over_history(self, line, status, line_type, budget_line_field, budget_line):
        for rec in self:
            if line_type == 'labour':
                if status == 'send':
                    self.env['labour.budget.carry.over.history'].create({
                        'project_budget_id': rec.from_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_send_time': line.time,
                        'carry_send_contractors': line.contractors,
                        'carry_send_amt': line.unit_price * line.contractors * line.time,
                        'carried_to_id': rec.to_project_budget_id.id,
                    })
                else:
                    self.env['labour.budget.carry.over.history'].create({
                        'project_budget_id': rec.to_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_from_time': line.time,
                        'carry_from_contractors': line.contractors,
                        'carry_from_amt': line.unit_price * line.contractors * line.time,
                        'carried_from_id': rec.from_project_budget_id.id,
                    })
            elif line_type == 'internal_asset':
                if status == 'send':
                    self.env['internal.asset.budget.carry.over.history'].create({
                        'project_budget_id': rec.from_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'asset_category_id': line.asset_category_id.id,
                        'asset_id': line.asset_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price * line.quantity,
                        'carried_to_id': rec.to_project_budget_id.id,
                    })
                else:
                    self.env['internal.asset.budget.carry.over.history'].create({
                        'project_budget_id': rec.to_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'asset_category_id': line.asset_category_id.id,
                        'asset_id': line.asset_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price * line.quantity,
                        'carried_from_id': rec.from_project_budget_id.id,
                    })
            elif line_type == 'overhead':
                if status == 'send':
                    self.env['overhead.budget.carry.over.history'].create({
                        'project_budget_id': rec.from_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'overhead_category': line.overhead_category,
                        'product_id': line.product_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price * line.quantity,
                        'carried_to_id': rec.to_project_budget_id.id,
                    })
                else:
                    self.env['overhead.budget.carry.over.history'].create({
                        'project_budget_id': rec.to_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'overhead_category': line.overhead_category,
                        'product_id': line.product_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price * line.quantity,
                        'carried_from_id': rec.from_project_budget_id.id,
                    })
            elif line_type == 'subcon':
                if status == 'send':
                    self.env['subcon.budget.carry.over.history'].create({
                        'project_budget_id': rec.from_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'subcon_id': line.subcon_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price * line.quantity,
                        'carried_to_id': rec.to_project_budget_id.id,
                    })
                else:
                    self.env['subcon.budget.carry.over.history'].create({
                        'project_budget_id': rec.to_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'subcon_id': line.subcon_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price * line.quantity,
                        'carried_from_id': rec.from_project_budget_id.id,
                    })
            elif line_type == 'material':
                if status == 'send':
                    self.env['material.budget.carry.over.history'].create({
                        'project_budget_id': rec.from_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price * line.quantity,
                        'carried_to_id': rec.to_project_budget_id.id,
                    })
                else:
                    self.env['material.budget.carry.over.history'].create({
                        'project_budget_id': rec.to_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price * line.quantity,
                        'carried_from_id': rec.from_project_budget_id.id,
                    })
            elif line_type == 'equipment':
                if status == 'send':
                    self.env['equipment.budget.carry.over.history'].create({
                        'project_budget_id': rec.from_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price * line.quantity,
                        'carried_to_id': rec.to_project_budget_id.id,
                    })
                else:
                    self.env['equipment.budget.carry.over.history'].create({
                        'project_budget_id': rec.to_project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price * line.quantity,
                        'carried_from_id': rec.from_project_budget_id.id,
                    })

    def btn_submit(self):
        for rec in self:
            carry_from = rec.from_project_budget_id
            carry_to = rec.to_project_budget_id
            # write state and carried to field in project budget
            # Material Estimation
            if rec.budget_carry_material_ids:
                for line in rec.budget_carry_material_ids:
                    material = []
                    budget_material = line.bd_material_id
                    if budget_material.group_of_product.is_carry_over == True and budget_material.qty_left != 0.0 and budget_material.amt_left != 0.0:
                        same_material = carry_to.budget_material_ids.filtered(lambda
                                                                                  x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)
                        if carry_to.state not in ['in_progress', 'complete']:
                            budget_material.cs_material_id.allocated_budget_amt -= line.quantity * line.unit_price
                            budget_material.cs_material_id.allocated_budget_qty -= line.quantity
                            if same_material:
                                same_material.unallocated_amount += line.quantity * line.unit_price
                                same_material.unallocated_quantity += line.quantity
                                same_material.quantity += line.quantity
                            else:
                                material.append((0, 0, {
                                    'cs_material_id': budget_material.cs_material_id.id or False,
                                    'project_scope': budget_material.project_scope.id or False,
                                    'section_name': budget_material.section_name.id or False,
                                    'variable': budget_material.variable.id or False,
                                    'group_of_product': budget_material.group_of_product.id or False,
                                    'product_id': budget_material.product_id.id or False,
                                    'description': budget_material.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_material.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                    'unallocated_amount': line.quantity * line.unit_price,
                                    'unallocated_quantity': line.quantity,
                                }))
                        else:
                            if same_material:
                                same_material.quantity += line.quantity
                                same_material.carried_from = carry_from.id
                            else:
                                material.append((0, 0, {
                                    'cs_material_id': budget_material.cs_material_id.id or False,
                                    'project_scope': budget_material.project_scope.id or False,
                                    'section_name': budget_material.section_name.id or False,
                                    'variable': budget_material.variable.id or False,
                                    'group_of_product': budget_material.group_of_product.id or False,
                                    'product_id': budget_material.product_id.id or False,
                                    'description': budget_material.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_material.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                }))

                        budget_material.update({'quantity': budget_material.quantity - line.quantity,
                                                'status': 'carried_over',
                                                'carried_to': carry_to.id,
                                                })

                    rec.set_carry_over_history(line, 'send', 'material', 'bd_material_id', budget_material)
                    rec.set_carry_over_history(line, 'receive', 'material', 'bd_material_id', budget_material)

                    carry_to.update({'budget_material_ids': material})
                if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(rec.budget_carry_material_ids) > 0:
                    rec.to_project_budget_id.get_gop_material_table()

            # Labour Estimation
            if rec.budget_carry_Labour_ids:
                for line in rec.budget_carry_Labour_ids:
                    labour = []
                    budget_labour = line.bd_labour_id
                    if budget_labour.group_of_product.is_carry_over == True and budget_labour.time_left != 0.0 and budget_labour.amt_left != 0.0:
                        same_labour = carry_to.budget_labour_ids.filtered(lambda
                                                                              x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)
                        if carry_to.state not in ['in_progress', 'complete']:
                            budget_labour.cs_labour_id.allocated_budget_amt -= line.time * line.contractors * line.unit_price
                            budget_labour.cs_labour_id.allocated_budget_time -= line.time
                            budget_labour.cs_labour_id.allocated_contractors -= line.contractors
                            # budget_labour.cs_labour_id.allocated_budget_qty -= line.quantity
                            if same_labour:
                                same_labour.unallocated_amount += line.time * line.contractors * line.unit_price
                                same_labour.unallocated_time += line.time
                                same_labour.unallocated_contractors += line.contractors
                                same_labour.time += line.time
                                same_labour.contractors += line.contractors
                            else:
                                labour.append((0, 0, {
                                    'cs_labour_id': budget_labour.cs_labour_id.id or False,
                                    'project_scope': budget_labour.project_scope.id or False,
                                    'section_name': budget_labour.section_name.id or False,
                                    'variable': budget_labour.variable.id or False,
                                    'group_of_product': budget_labour.group_of_product.id or False,
                                    'product_id': budget_labour.product_id.id or False,
                                    'description': budget_labour.description or False,
                                    'time': line.time or False,
                                    'amount': line.unit_price or False,
                                    'contractors': line.contractors or False,
                                    'uom_id': budget_labour.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                    'unallocated_amount': line.time * line.contractors * line.unit_price,
                                    'unallocated_time': line.time,
                                    'unallocated_contractors': line.contractors,
                                    # 'unallocated_quantity': line.quantity,
                                }))
                        else:
                            if same_labour:
                                same_labour.time += line.time
                                same_labour.contractors += line.contractors
                                same_labour.carried_from = carry_from.id
                            else:
                                labour.append((0, 0, {
                                    'cs_labour_id': budget_labour.cs_labour_id.id or False,
                                    'project_scope': budget_labour.project_scope.id or False,
                                    'section_name': budget_labour.section_name.id or False,
                                    'variable': budget_labour.variable.id or False,
                                    'group_of_product': budget_labour.group_of_product.id or False,
                                    'product_id': budget_labour.product_id.id or False,
                                    'description': budget_labour.description or False,
                                    'time': line.time or False,
                                    'amount': line.unit_price or False,
                                    'contractors': line.contractors or False,
                                    'uom_id': budget_labour.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                }))

                        budget_labour.update({'time': budget_labour.time - line.time,
                                              'contractors': budget_labour.contractors - line.contractors,
                                              'status': 'carried_over',
                                              'carried_to': carry_to.id
                                              })

                    rec.set_carry_over_history(line, 'send', 'labour', 'bd_labour_id', budget_labour)
                    rec.set_carry_over_history(line, 'receive', 'labour', 'bd_labour_id', budget_labour)

                    carry_to.update({'budget_labour_ids': labour})
                    if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(
                            rec.budget_carry_Labour_ids) > 0:
                        rec.to_project_budget_id.get_gop_labour_table()

            # Internal Asset
            if rec.budget_carry_internal_asset_ids:
                for line in rec.budget_carry_internal_asset_ids:
                    internal_asset = []
                    budget_internal_asset = line.bd_internal_asset_id
                    if budget_internal_asset.budgeted_qty_left != 0.0 and budget_internal_asset.budgeted_amt_left != 0.0:
                        same_asset = carry_to.budget_internal_asset_ids.filtered(lambda
                                                                                     x: x.project_scope_line_id.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.asset_category_id.id == line.asset_category_id.id and x.asset_id.id == line.asset_id.id)
                        if carry_to.state not in ['in_progress', 'complete']:
                            budget_internal_asset.cs_internal_asset_id.allocated_budget_amt -= line.quantity * line.unit_price
                            budget_internal_asset.cs_internal_asset_id.allocated_budget_qty -= line.quantity
                            if same_asset:
                                same_asset.unallocated_budget_amt += line.quantity * line.unit_price
                                same_asset.unallocated_budget_qty += line.quantity
                                same_asset.budgeted_qty += line.quantity
                            else:
                                internal_asset.append((0, 0, {
                                    'cs_internal_asset_id': budget_internal_asset.cs_internal_asset_id.id or False,
                                    'project_scope_line_id': budget_internal_asset.project_scope_line_id.id or False,
                                    'section_name': budget_internal_asset.section_name.id or False,
                                    'variable_id': budget_internal_asset.variable_id.id or False,
                                    'asset_category_id': budget_internal_asset.asset_category_id.id or False,
                                    'asset_id': budget_internal_asset.asset_id.id or False,
                                    # 'description': budget_internal_asset.description or False,
                                    'budgeted_qty': line.quantity or False,
                                    'price_unit': line.unit_price or False,
                                    'uom_id': budget_internal_asset.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                    'unallocated_budget_amt': line.quantity * line.unit_price,
                                    'unallocated_budget_qty': line.quantity,
                                }))
                        else:
                            if same_asset:
                                same_asset.budgeted_qty += line.quantity
                                same_asset.carried_from = carry_from.id
                            else:
                                internal_asset.append((0, 0, {
                                    'cs_internal_asset_id': budget_internal_asset.cs_internal_asset_id.id or False,
                                    'project_scope_line_id': budget_internal_asset.project_scope_line_id.id or False,
                                    'section_name': budget_internal_asset.section_name.id or False,
                                    'variable_id': budget_internal_asset.variable_id.id or False,
                                    'asset_category_id': budget_internal_asset.asset_category_id.id or False,
                                    'asset_id': budget_internal_asset.asset_id.id or False,
                                    # 'description': budget_internal_asset.description or False,
                                    'budgeted_qty': line.quantity or False,
                                    'price_unit': line.unit_price or False,
                                    'uom_id': budget_internal_asset.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                }))

                        budget_internal_asset.update({'budgeted_qty': budget_internal_asset.budgeted_qty - line.quantity,
                                                      'status': 'carried_over',
                                                      'carried_to': carry_to.id,
                                                      })

                    rec.set_carry_over_history(line, 'send', 'internal_asset', 'bd_internal_asset_id', budget_internal_asset)
                    rec.set_carry_over_history(line, 'receive', 'internal_asset', 'bd_internal_asset_id', budget_internal_asset)

                    carry_to.update({'budget_internal_asset_ids': internal_asset})

            # Equipment Lease Estimation
            if rec.budget_carry_equipment_ids:
                for line in rec.budget_carry_equipment_ids:
                    equipment = []
                    budget_equipment = line.bd_equipment_id
                    if budget_equipment.group_of_product.is_carry_over == True and budget_equipment.qty_left != 0.0 and budget_equipment.amt_left != 0.0:
                        same_equipment = carry_to.budget_equipment_ids.filtered(lambda
                                                                                    x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)
                        if carry_to.state not in ['in_progress', 'complete']:
                            budget_equipment.cs_equipment_id.allocated_budget_amt -= line.quantity * line.unit_price
                            budget_equipment.cs_equipment_id.allocated_budget_qty -= line.quantity
                            if same_equipment:
                                same_equipment.unallocated_amount += line.quantity * line.unit_price
                                same_equipment.unallocated_quantity += line.quantity
                                same_equipment.quantity += line.quantity
                            else:
                                equipment.append((0, 0, {
                                    'cs_equipment_id': budget_equipment.cs_equipment_id.id or False,
                                    'project_scope': budget_equipment.project_scope.id or False,
                                    'section_name': budget_equipment.section_name.id or False,
                                    'variable': budget_equipment.variable.id or False,
                                    'group_of_product': budget_equipment.group_of_product.id or False,
                                    'product_id': budget_equipment.product_id.id or False,
                                    'description': budget_equipment.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_equipment.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                    'unallocated_amount': line.quantity * line.unit_price,
                                    'unallocated_quantity': line.quantity,
                                }))
                        else:
                            if same_equipment:
                                same_equipment.quantity += line.quantity
                                same_equipment.carried_from = carry_from.id
                            else:
                                equipment.append((0, 0, {
                                    'cs_equipment_id': budget_equipment.cs_equipment_id.id or False,
                                    'project_scope': budget_equipment.project_scope.id or False,
                                    'section_name': budget_equipment.section_name.id or False,
                                    'variable': budget_equipment.variable.id or False,
                                    'group_of_product': budget_equipment.group_of_product.id or False,
                                    'product_id': budget_equipment.product_id.id or False,
                                    'description': budget_equipment.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_equipment.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                }))

                        budget_equipment.update({'quantity': budget_equipment.quantity - line.quantity,
                                                 'status': 'carried_over',
                                                 'carried_to': carry_to.id,
                                                 })

                    rec.set_carry_over_history(line, 'send', 'equipment', 'bd_equipment_id', budget_equipment)
                    rec.set_carry_over_history(line, 'receive', 'equipment', 'bd_equipment_id', budget_equipment)

                    carry_to.update({'budget_equipment_ids': equipment})
                    if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(
                            rec.budget_carry_equipment_ids) > 0:
                        rec.to_project_budget_id.get_gop_equipment_table()

            #  Subcon Estimation
            if rec.budget_carry_subcon_ids:
                for line in rec.budget_carry_subcon_ids:
                    subcon = []
                    budget_subcon = line.bd_subcon_id
                    if budget_subcon.qty_left != 0.0 and budget_subcon.amt_left != 0.0:
                        same_subcon = carry_to.budget_subcon_ids.filtered(lambda
                                                                              x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.subcon_id.id == line.subcon_id.id)
                        if carry_to.state not in ['in_progress', 'complete']:
                            budget_subcon.cs_subcon_id.allocated_budget_amt -= line.quantity * line.unit_price
                            budget_subcon.cs_subcon_id.allocated_budget_qty -= line.quantity
                            if same_subcon:
                                same_subcon.unallocated_amount += line.quantity * line.unit_price
                                same_subcon.unallocated_quantity += line.quantity
                                same_subcon.quantity += line.quantity
                            else:
                                subcon.append((0, 0, {
                                    'cs_subcon_id': budget_subcon.cs_subcon_id.id or False,
                                    'project_scope': budget_subcon.project_scope.id or False,
                                    'section_name': budget_subcon.section_name.id or False,
                                    'variable_ref': budget_subcon.variable_ref.id or False,
                                    'subcon_id': budget_subcon.subcon_id.id or False,
                                    'description': budget_subcon.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_subcon.uom_id.id or False,
                                    'status': 'carried_over',
                                    'unallocated_amount': line.quantity * line.unit_price,
                                    'unallocated_quantity': line.quantity,
                                }))
                        else:
                            if same_subcon:
                                same_subcon.quantity += line.quantity
                                same_subcon.carried_from = carry_from.id
                            else:
                                subcon.append((0, 0, {
                                    'cs_subcon_id': budget_subcon.cs_subcon_id.id or False,
                                    'project_scope': budget_subcon.project_scope.id or False,
                                    'section_name': budget_subcon.section_name.id or False,
                                    'variable_ref': budget_subcon.variable_ref.id or False,
                                    'subcon_id': budget_subcon.subcon_id.id or False,
                                    'description': budget_subcon.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_subcon.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                }))

                        budget_subcon.update({'quantity': budget_subcon.quantity - line.quantity,
                                              'status': 'carried_over',
                                              'carried_to': carry_to.id,
                                              })

                    rec.set_carry_over_history(line, 'send', 'subcon', 'bd_subcon_id', budget_subcon)
                    rec.set_carry_over_history(line, 'receive', 'subcon', 'bd_subcon_id', budget_subcon)

                    carry_to.update({'budget_subcon_ids': subcon})

            # Overhead Estimation
            if rec.budget_carry_overhead_ids:
                for line in rec.budget_carry_overhead_ids:
                    overhead = []
                    budget_overhead = line.bd_overhead_id
                    if budget_overhead.group_of_product.is_carry_over == True and budget_overhead.qty_left != 0.0 and budget_overhead.amt_left != 0.0:
                        same_overhead = carry_to.budget_overhead_ids.filtered(lambda
                                                                                  x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)

                        if carry_to.state not in ['in_progress', 'complete']:
                            budget_overhead.cs_overhead_id.allocated_budget_amt -= line.quantity * line.unit_price
                            budget_overhead.cs_overhead_id.allocated_budget_qty -= line.quantity
                            if same_overhead:
                                same_overhead.unallocated_amount += line.quantity * line.unit_price
                                same_overhead.unallocated_quantity += line.quantity
                                same_overhead.quantity += line.quantity
                            else:
                                overhead.append((0, 0, {
                                    'cs_overhead_id': budget_overhead.cs_overhead_id.id or False,
                                    'project_scope': budget_overhead.project_scope.id or False,
                                    'section_name': budget_overhead.section_name.id or False,
                                    'variable': budget_overhead.variable.id or False,
                                    'group_of_product': budget_overhead.group_of_product.id or False,
                                    'overhead_catagory': budget_overhead.overhead_catagory or False,
                                    'product_id': budget_overhead.product_id.id or False,
                                    'description': budget_overhead.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_overhead.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                    'unallocated_amount': line.quantity * line.unit_price,
                                    'unallocated_quantity': line.quantity,
                                }))
                        else:
                            if same_overhead:
                                same_overhead.quantity += line.quantity
                                same_overhead.carried_from = carry_from.id
                            else:
                                overhead.append((0, 0, {
                                    'cs_overhead_id': budget_overhead.cs_overhead_id.id or False,
                                    'project_scope': budget_overhead.project_scope.id or False,
                                    'section_name': budget_overhead.section_name.id or False,
                                    'variable': budget_overhead.variable.id or False,
                                    'group_of_product': budget_overhead.group_of_product.id or False,
                                    'overhead_catagory': budget_overhead.overhead_catagory or False,
                                    'product_id': budget_overhead.product_id.id or False,
                                    'description': budget_overhead.description or False,
                                    'quantity': line.quantity or False,
                                    'amount': line.unit_price or False,
                                    'uom_id': budget_overhead.uom_id.id or False,
                                    'status': 'carried_over',
                                    'carried_from': carry_from.id,
                                }))

                        budget_overhead.update({'quantity': budget_overhead.quantity - line.quantity,
                                                'status': 'carried_over',
                                                'carried_to': carry_to.id,
                                                })

                    rec.set_carry_over_history(line, 'send', 'overhead', 'bd_overhead_id', budget_overhead)
                    rec.set_carry_over_history(line, 'receive', 'overhead', 'bd_overhead_id', budget_overhead)

                    carry_to.update({'budget_overhead_ids': overhead})
                    if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(
                            rec.budget_carry_overhead_ids) > 0:
                        rec.to_project_budget_id.get_gop_overhead_table()

            rec.write({'state': 'done'})

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.budget.carry.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            }

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                    }

    @api.onchange('to_project_budget_id', 'from_project_budget_id')
    def _to_from_project_budget(self):
        if self.from_project_budget_id and self.to_project_budget_id:
            if self.from_project_budget_id.id == self.to_project_budget_id.id:
                raise ValidationError(_("You can not choose same project budget."))


class BudgetCarryOverApproverUser(models.Model):
    _name = 'budget.carry.approver.user'
    _description = 'Budget Carry Over Approver User'

    budget_carry_approver_id = fields.Many2one('project.budget.carry', string="Budget Carry Over", ondelete="cascade")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'budget_carry_app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'carry_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(related='budget_carry_approver_id.state', string='Parent Status')

    @api.depends('budget_carry_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.budget_carry_approver_id.budget_carry_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.budget_carry_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.budget_carry_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids
