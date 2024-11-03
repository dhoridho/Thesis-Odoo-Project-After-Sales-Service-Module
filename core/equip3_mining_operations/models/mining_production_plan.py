from odoo import api, fields, models, _
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import ValidationError


class MiningPordPlan(models.Model):
    _name = 'mining.production.plan'
    _description = 'Production Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mining.production.plan', sequence_date=None) or _('New')
        records = super(MiningPordPlan, self).create(vals)
        records._setup_mining_prod_line()
        return records
    
    def write(self, vals):
        res = super(MiningPordPlan, self).write(vals)
        if not vals.get('operation_ids', False) or self.env.context.get('skip_assign', False):
            return res
        self._setup_mining_prod_line()
        return res

    def _setup_mining_prod_line(self):
        env_prod_line = self.env['mining.production.line']
        for record in self:
            for operation in record.operation_ids:
                prod_line_id = operation.mining_prod_line_id
                if prod_line_id:
                    if not prod_line_id.mining_prod_plan_id:
                        prod_line_id.write({'mining_prod_plan_id': record.id})
                else:
                    prod_line_vals = record._prepare_mining_prod_line_values(operation)
                    for field_name in ('assets_ids', 'input_ids', 'output_ids', 'fuel_ids', 'delivery_ids'):
                        record_operation = record[field_name].filtered(lambda x: x.operation_id == operation.operation_id)
                        field_name_ids = record_operation.filtered(lambda x: not x.mining_prod_line_id)
                        if not field_name_ids and record_operation:
                            field_name_ids = self.env[record[field_name]._name]
                            for rec in record_operation.filtered(lambda x: x.original_move):
                                field_name_ids |= rec.copy({'original_move': True})
                        prod_line_vals[field_name] = [(6, 0, field_name_ids.ids)]
                    operation.mining_prod_line_id = env_prod_line.create(prod_line_vals).id

    def _prepare_mining_prod_line_values(self, operation):
        self.ensure_one()
        values = {
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'mining_prod_plan_id' : self.id,
            'mining_site_id' : self.mining_site_id.id,
            'mining_project_id' : self.mining_project_id.id,
            'period_from' : self.period_from,
            'period_to' : self.period_to,
            'analytic_group_ids' : [(6, 0, self.analytic_group_ids.ids)],
            'worker_type' : self.worker_type,
            'worker_ids' : [(6, 0, self.worker_ids.ids)],
            'worker_group_id' : self.worker_group_id.id,
            'ppic_id' : operation.ppic_id.id,
            'operation_id' : operation.operation_id.id,
            'operation_type' : operation.operation_id.operation_type_id,
        }
        if self.company_id.mining_production_line:
            approval_matrix_id = self.env['mining.production.line']._default_approval_matrix(company=self.company_id, branch=self.branch_id)
            if not approval_matrix_id:
                raise ValidationError(_('Please set approval matrix for Production Line first!'))
            values['approval_matrix_id'] = approval_matrix_id
        return values
    
    @api.model
    def _default_analytic_tag_ids(self):
        user = self.env.user
        analytic_priority = self.env['analytic.priority'].sudo().search([], limit=1, order='priority')
        analytic_tag_ids = []
        if analytic_priority.object_id == 'user' and user.analytic_tag_ids:
            analytic_tag_ids = user.analytic_tag_ids.ids
        elif analytic_priority.object_id == 'branch' and user.branch_id and user.branch_id.analytic_tag_ids:
            analytic_tag_ids = user.branch_id.analytic_tag_ids.ids
        elif analytic_priority.object_id == 'product_category':
            product_category = self.env['product.category'].sudo().search([('analytic_tag_ids', '!=', False)], limit=1)
            analytic_tag_ids = product_category.analytic_tag_ids.ids
        return [(6, 0, analytic_tag_ids)]
    
    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.mining_production_plan:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mining.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'mpp')
        ], limit=1).id

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = [(5,)]
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'mpp_id': record.id,
                        'line_id': line.id,
                        'sequence': line.sequence,
                        'minimum_approver': line.minimum_approver,
                        'approver_ids': [(6, 0, line.approver_ids.ids)]
                    })]
            record.approval_matrix_line_ids = lines

    @api.depends('approval_matrix_line_ids', 'approval_matrix_line_ids.need_action_ids', 'is_matrix_on')
    def _compute_user_is_approver(self):
        user = self.env.user
        for record in self:
            need_action_ids = record.approval_matrix_line_ids.mapped('need_action_ids')
            record.user_is_approver = user in need_action_ids and record.is_matrix_on


    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    name = fields.Char(string='Production Plan', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    mining_site_id = fields.Many2one('mining.site.control', string='Mining Site Name', required=True, tracking=True)
    mining_project_id = fields.Many2one('mining.project.control', domain="[('mining_site_id', '=', mining_site_id)]", string='Mining Pit', required=True, tracking=True)
    ppic_id = fields.Many2one('res.users', string='PPIC', default=lambda self: self.env.user, required=True, tracking=True)
    period_from = fields.Date(string='Period', required=True, tracking=True)
    period_to = fields.Date(string='Period End', required=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True, readonly=True, tracking=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, tracking=True)
    analytic_group_ids = fields.Many2many(
        comodel_name='account.analytic.tag', 
        domain="[('company_id', '=', company_id)]", 
        string="Analytic Group", 
        readonly=True, 
        states={'draft': [('readonly', False)]}, 
        default=_default_analytic_tag_ids)
    
    approval_matrix_id = fields.Many2one(
        comodel_name='mining.approval.matrix', 
        domain="[('matrix_type', '=', 'mpp')]",
        string='Approval Matrix', 
        default=_default_approval_matrix,
        readonly=True)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='mining.approval.matrix.entry',
        inverse_name='mpp_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    is_matrix_on = fields.Boolean(related='company_id.mining_production_plan')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='State', default='draft', tracking=True)

    worker_type = fields.Selection(selection=[
        ('with_group', 'With Group'),
        ('without_group', 'Without Group')
    ], default='with_group', string='Worker Type')
    worker_ids = fields.Many2many(comodel_name='hr.employee', string='Worker')
    worker_group_id = fields.Many2one(comodel_name='mining.worker.group', string='Worker Group')
    
    operation_ids = fields.One2many(comodel_name='mining.production.plan.operations', inverse_name='mining_prod_plan_id', string='Mining Production Plan Operations')
    assets_ids = fields.One2many(comodel_name='mining.production.plan.assets', inverse_name='mining_prod_plan_id', string='Mining Production Plan Assets')
    input_ids = fields.One2many(comodel_name='mining.production.plan.input', inverse_name='mining_prod_plan_id', string='Mining Production Plan Input')
    output_ids = fields.One2many(comodel_name='mining.production.plan.output', inverse_name='mining_prod_plan_id', string='Mining Production Plan Output')
    fuel_ids = fields.One2many(comodel_name='mining.production.plan.fuel', inverse_name='mining_prod_plan_id', string='Mining Production Plan Fuel')
    delivery_ids = fields.One2many(comodel_name='mining.production.plan.delivery', inverse_name='mining_prod_plan_id', string='Mining Production Plan Delivery')

    # technical fields
    state_1 = fields.Selection(related='state', tracking=False, string='State 1')
    state_2 = fields.Selection(related='state', tracking=False, string='State 2')

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        if not self.company_id or not self.branch_id:
            self.approval_matrix_id = False
            return
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)

    @api.onchange('worker_type')
    def _onchange_worker_type(self):
        if self.worker_type != 'with_group':
            self.worker_group_id = False

    @api.onchange('worker_group_id')
    def _onchange_worker_group_id(self):
        if self.worker_type != 'with_group':
            worker_ids = [(5,)]
        else:
            worker_ids = []
            if self.worker_group_id:
                worker_ids = self.worker_group_id.worker_ids.ids
        self.worker_ids = [(6, 0, worker_ids)]

    @api.onchange('worker_ids')
    def _onchange_worker_ids(self):
        self.assets_ids.update({'worker_ids': [(6, 0, self.worker_ids.ids)]})

    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.mining_production_plan_wa_notif
            }
            record.approval_matrix_id.action_approval(record, options=options)
            record.write({'state': 'to_be_approved'})
            record.operation_ids.mapped('mining_prod_line_id').action_approval()

    def action_approve(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})
                record.operation_ids.mapped('mining_prod_line_id').action_approve()

    def action_reject(self, reason=False):
        for record in self:
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)
            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'rejected'})
                record.operation_ids.mapped('mining_prod_line_id').action_reject()

    def action_toggle_matrix(self, is_on):
        matrix = self.env['mining.approval.matrix']
        valid_state = is_on and 'draft' or 'to_be_approved'
        for record in self:
            if record.state != valid_state:
                continue
            matrix.toggle_on_off(record, is_on)
            if is_on:
                continue
            record.write({'state': 'draft'})

    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirm'

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    def action_actualization(self):
        self.ensure_one()
        return {
            'name': _('Actualization'),
            'type': 'ir.actions.act_window',
            'res_model': 'action.actualization.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_mining_prod_plan_id': self.id}
        }

    def action_done(self):
        self.ensure_one()
        for line in self.operation_ids.mapped('mining_prod_line_id'):
            line.action_done()
        self.state = 'done'
