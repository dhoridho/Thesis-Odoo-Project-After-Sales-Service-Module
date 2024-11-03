from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.addons.equip3_mining_operations.models.mining_operations_two import OPERATION_TYPES


class MiningProdLine(models.Model):
    _name = 'mining.production.line'
    _description = 'Production Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def name_get(self):
        result = super(MiningProdLine, self).name_get()
        if not self.env.context.get('show_actualization_count', False):
            return result
        new_result = []
        for record, (record_id, record_name) in zip(self, result):
            name = '%s (%s Actualizations)' % (record_name, len(record.actualization_ids))
            new_result += [(record_id, name)]
        return new_result
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mining.production.line', sequence_date=None) or _('New')
        records = super(MiningProdLine, self).create(vals)
        should_assign_plan = self.env.context.get('should_assign_plan', False)
        if not should_assign_plan:
            return records
        prod_operation = self.env['mining.production.plan.operations']
        for record in records:
            if not record.mining_prod_plan_id:
                continue

            if record.mining_prod_plan_id.state not in ('draft', 'to_be_approved'):
                continue

            operation_vals = {
                'mining_prod_plan_id': record.mining_prod_plan_id.id,
                'mining_prod_line_id': record.id,
                'operation_id': record.operation_id and record.operation_id.id or False,
                'ppic_id': record.ppic_id and record.ppic_id.id or False,
                'notes': 'added from production lines'
            }

            prod_operation.create(operation_vals)

            for field_name in ('assets_ids', 'input_ids', 'output_ids', 'fuel_ids', 'delivery_ids'):
                record.mining_prod_plan_id.with_context(skip_assign=True).write({field_name: [(4, field.id) for field in record[field_name]]})
        return records

    def write(self, vals):
        res = super(MiningProdLine, self).write(vals)
        should_assign_plan = self.env.context.get('should_assign_plan', False)
        if not any(key in vals for key in ('mining_prod_plan_id', 'operation_id', 'ppic_id')) or not should_assign_plan:
            return res
        prod_operation = self.env['mining.production.plan.operations']
        for record in self:
            if not record.mining_prod_plan_id:
                continue

            if record.mining_prod_plan_id.state not in ('draft', 'to_be_approved'):
                continue
            
            operation_ids = prod_operation.search([('mining_prod_line_id', '=', record.id)])
            operation_vals = {
                'mining_prod_plan_id': record.mining_prod_plan_id.id,
                'operation_id': record.operation_id and record.operation_id.id or False,
                'ppic_id': record.ppic_id and record.ppic_id.id or False,
            }

            if operation_ids:
                operation_ids.write(operation_vals)
            else:
                operation_vals.update({
                    'mining_prod_line_id': record.id,
                    'notes': 'added from production lines'
                })
                prod_operation.create(operation_vals)

            for field_name in ('assets_ids', 'input_ids', 'output_ids', 'fuel_ids', 'delivery_ids'):
                record.mining_prod_plan_id.with_context(skip_assign=True).write({field_name: [(4, field.id) for field in record[field_name]]})
        return res

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
        if not company.mining_production_line:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mining.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'mpl')
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
                        'mpl_id': record.id,
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

    @api.depends('mining_prod_plan_id', 'mining_site_id')
    def _compute_mining_prod_plan_id(self):
        prod_confs = self.env['mining.production.conf'].search([])
        for record in self:
            site_id = False
            if record.mining_prod_plan_id:
                site_id = record.mining_prod_plan_id.mining_site_id or record.mining_site_id
            operation_ids = prod_confs.filtered(lambda p: p.site_id == site_id).mapped('operation_id')
            record.operation_ids = [(6, 0, operation_ids.ids)]


    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    name = fields.Char(string='Production Lines', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    
    mining_prod_plan_id = fields.Many2one(comodel_name='mining.production.plan', string='Production Plan', domain="[('state', 'in', ('draft', 'to_be_approved'))]", tracking=True)
    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, tracking=True)
    
    mining_site_id = fields.Many2one('mining.site.control', string='Mining Site Name', required=True, tracking=True)
    mining_project_id = fields.Many2one('mining.project.control', domain="[('mining_site_id', '=', mining_site_id)]", string='Mining Pit', required=True, tracking=True)
    ppic_id = fields.Many2one('res.users', default=lambda self: self.env.user, string='PPIC', required=True, tracking=True)
    
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
        domain="[('matrix_type', '=', 'mpl')]",
        string='Approval Matrix', 
        default=_default_approval_matrix,
        readonly=True)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='mining.approval.matrix.entry',
        inverse_name='mpl_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    is_matrix_on = fields.Boolean(related='company_id.mining_production_line')
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

    operation_type = fields.Selection(selection=OPERATION_TYPES, string='Operation Type')
    
    assets_ids = fields.One2many(comodel_name='mining.production.plan.assets', inverse_name='mining_prod_line_id', string='Mining Production Lines Assets')
    input_ids = fields.One2many(comodel_name='mining.production.plan.input', inverse_name='mining_prod_line_id', string='Mining Production Lines Input')
    output_ids = fields.One2many(comodel_name='mining.production.plan.output', inverse_name='mining_prod_line_id', string='Mining Production Lines Output')
    operation_ids = fields.Many2many(comodel_name='mining.operations.two', string='Operation', compute="_compute_mining_prod_plan_id")
    fuel_ids = fields.One2many(comodel_name='mining.production.plan.fuel', inverse_name='mining_prod_line_id', string='Mining Production Lines Fuel')
    delivery_ids = fields.One2many(comodel_name='mining.production.plan.delivery', inverse_name='mining_prod_line_id', string='Mining Production Lines Delivery')
    actualization_ids = fields.One2many(comodel_name='mining.production.actualization', inverse_name='mining_prod_line_id', string='Mining Production Actualizations', readonly=True)

    # technical fields
    state_1 = fields.Selection(related='state', tracking=False, string='State 1')
    state_2 = fields.Selection(related='state', tracking=False, string='State 2')

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        if not self.company_id or not self.branch_id:
            self.approval_matrix_id = False
            return
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)
        
    @api.onchange('operation_id')
    def _onchange_operation_type(self):
        self.operation_type = False
        if self.operation_id:
            self.operation_type = self.operation_id.operation_type_id
        for field_name in ('assets_ids', 'input_ids', 'output_ids', 'fuel_ids'):
            self[field_name].update({'operation_id': self.operation_id and self.operation_id.id or False})

    @api.onchange('worker_type')
    def _onchange_worker_type(self):
        if self.worker_type != 'with_gruop':
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

    @api.onchange('mining_prod_plan_id')
    def _onchange_mining_prod_plan_id(self):
        prod_plan_id = self.mining_prod_plan_id
        if prod_plan_id:
            self.mining_site_id = prod_plan_id.mining_site_id.id
            self.mining_project_id = prod_plan_id.mining_project_id.id
            self.period_from = prod_plan_id.period_from
            self.period_to = prod_plan_id.period_to
            self.assets_ids.update({'mining_plan_prod_id': prod_plan_id.id})
            self.input_ids.update({'mining_plan_prod_id': prod_plan_id.id})
            self.output_ids.update({'mining_plan_prod_id': prod_plan_id.id})
            self.fuel_ids.update({'mining_plan_prod_id': prod_plan_id.id})

    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.mining_production_line_wa_notif
            }
            record.approval_matrix_id.action_approval(record, options=options)
            record.write({'state': 'to_be_approved'})

    def action_approve(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})

    def action_reject(self, reason=False):
        for record in self:
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)
            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'rejected'})

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

    def _prepare_production_actualization_vals(self):

        def ensure_exist(obj):
            return obj and obj.id or False

        self.ensure_one()
        values = {
            'mining_prod_plan_id': ensure_exist(self.mining_prod_plan_id),
            'mining_prod_line_id': ensure_exist(self),
            'mining_site_id': ensure_exist(self.mining_site_id),
            'mining_project_id': ensure_exist(self.mining_project_id),
            'period_from': self.period_from,
            'period_to': self.period_to,
            'operation_id': ensure_exist(self.operation_id),
            'operation_type': self.operation_type,
            'ppic_id': ensure_exist(self.ppic_id),
            'company_id': ensure_exist(self.company_id),
            'branch_id': ensure_exist(self.branch_id),
            'analytic_group_ids': [(6, 0, self.analytic_group_ids.ids)],
            'worker_type': self.worker_type,
            'worker_group_id': ensure_exist(self.worker_group_id),
            'worker_ids': [(6, 0, self.worker_ids.ids)],
        }

        if self.company_id.mining_production_act:
            approval_matrix_id = self.env['mining.production.actualization']._default_approval_matrix(company=self.company_id, branch=self.branch_id)
            if not approval_matrix_id:
                raise ValidationError(_('Please set approval matrix for Actualization first!'))
            values['approval_matrix_id'] = approval_matrix_id

        for field_name in ('assets_ids', 'input_ids', 'output_ids', 'fuel_ids', 'delivery_ids'):
            field_name_ids = self[field_name].filtered(lambda x: not x.mining_prod_act_id)
            if not field_name_ids and self[field_name]:
                field_name_ids = self.env[self[field_name]._name]
                for record in self[field_name].filtered(lambda x: x.original_move):
                    field_name_ids |= record.copy({'mining_prod_act_id': False})
            if field_name not in ('assets_ids', 'delivery_ids'):
                for field_name_id in field_name_ids:
                    field_name_id.qty_done = field_name_id.qty
            values[field_name] = [(6, 0, field_name_ids.ids)]
        return values

    def pop_actualization(self, act_id):
        return {
            'name': _('Actualization'),
            'type': 'ir.actions.act_window',
            'res_model': 'mining.production.actualization',
            'view_mode': 'form',
            'res_id': act_id,
            'target': 'new',
            'context': {'pop_back': True}
        }

    def action_actualization(self):
        self.ensure_one()
        if not self.mining_prod_plan_id:
            raise ValidationError(_('Please fill Production Plan Fields!'))
        record_id = self.actualization_ids.filtered(lambda r: r.state != 'confirm')
        if not record_id:
            vals = self._prepare_production_actualization_vals()
            record_id = self.env['mining.production.actualization'].create(vals)
        self.state = 'progress'
        if self.mining_prod_plan_id and self.mining_prod_plan_id.state == 'confirm':
            self.mining_prod_plan_id.state = 'progress'
        return self.pop_actualization(record_id[0].id)

    def action_done(self):
        self.ensure_one()
        self.state = 'done'
