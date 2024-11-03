from odoo import api, fields, models, _
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError, Warning


class CuttingPlan(models.Model):
    _name = 'cutting.plan'
    _description = 'Cutting Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    """
    cutting.plan
    Sequence = cutting.plan
    View = views/cutting_plan_views.xml
    Relation =
    cutting.order (cutting_order_ids)
    cutting.order.line (cutting_order_line_ids)
    sorted by priority, then date (check view)
    """

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'cutting.plan', sequence_date=None
            ) or _('New')
        return super(CuttingPlan, self).create(vals)

    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.is_cutting_plan:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mrp.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'cp')
        ], limit=1).id

    @api.model
    def _get_default_analytic_tag_ids(self):
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

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = []
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'cp_id': record.id,
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

    @api.depends('cutting_order_ids', 'cutting_order_ids.lot_ids')
    def _compute_cutting_order_lots(self):
        for record in self:
            lot_ids = record.cutting_order_ids.lot_ids.ids
            record.cutting_order_lot_ids = [(6, 0, lot_ids)]

    #Fields
    name = fields.Char(string='Cutting Plan', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)
    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True)
    
    plan_name = fields.Char(string='Plan Name')
    ppic_id = fields.Many2one(
        comodel_name='res.users',
        string='PPIC',
        required=False)

    date_start = fields.Datetime(
        string='Scheduled Date',
        default=fields.Datetime.now(),
        readonly=True,)

    date_end = fields.Datetime(
        string='To',
        default=fields.Datetime.now(),
        readonly=True)

    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytical Group',
        domain="[('company_id', '=', company_id)]",
        default=_get_default_analytic_tag_ids)

    ppic_id = fields.Many2one(
        'res.users',
        string='PPIC',
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        tracking=True,
        default=lambda self: self.env.company,
        readonly=True,)

    is_branch_required = fields.Boolean(related='company_id.show_branch')

    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True)

    create_uid = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,)

    create_date = fields.Date(
        string='Created On',
        default=fields.Date.today(),
        readonly=True,)

    approval_matrix_id = fields.Many2one(
        comodel_name='mrp.approval.matrix', 
        domain="""[
            ('matrix_type', '=', 'cp'),
            ('branch_id', '=', branch_id),
            ('company_id', '=', company_id)
        ]""",
        string='Approval Matrix', 
        default=_default_approval_matrix)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='mrp.approval.matrix.entry',
        inverse_name='cp_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    is_matrix_on = fields.Boolean(
        string='Is Matrix On', 
        related='company_id.is_cutting_plan')

    cutting_order_ids = fields.One2many(
        comodel_name='cutting.order', 
        inverse_name='cutting_plan_id',
        string='Cutting Order')

    cutting_order_lot_ids = fields.One2many(
        comodel_name='cutting.order.line',
        string='Cutting Order Line',
        compute=_compute_cutting_order_lots)

    memento_cutting_order = fields.Char(string='Memento')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    req_approval_datetime = fields.Datetime(string='Request Approval Date')

    # technical fields
    state_1 = fields.Selection(related='state', tracking=False, string='State 1')
    state_2 = fields.Selection(related='state', tracking=False, string='State 2')
    state_3 = fields.Selection(related='state', tracking=False, string='State 3')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)

    # Button Methods
    def button_confirm(self):
        self.ensure_one()
        if self.cutting_order_ids:
            for cutting_order in self.cutting_order_ids:
                cutting_order.button_confirm()
        self.state = 'confirm'

    def button_add_cutting(self):
        self.ensure_one()
        return {
            'name': 'Add Cutting Order',
            'res_model': 'cutting.plan.add.cutting.wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'default_cutting_plan_id': self.id},
            'target': 'new',
        }

    def button_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    def button_done(self):
        self.ensure_one()
        self.state = 'done'
        self.cutting_order_ids.button_done()

    def action_approval(self):
        is_whatsapp_notify = self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_cutting.send_whatsapp_notif_cp')
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': is_whatsapp_notify
            }
            record.approval_matrix_id.action_approval(record, options=options)
            if record.cutting_order_ids:
                for cutting_order in record.cutting_order_ids:
                    if cutting_order.approval_matrix_id == None:
                        raise Warning("Approval Matrix on Cutting Order must be filled")
                    cutting_order.action_approval()
            record.write({'state': 'to_be_approved'})

    def action_approve(self):
        for record in self:
            if record.cutting_order_ids:
                for cutting_order in record.cutting_order_ids:
                    cutting_order.action_approve()
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})

    def action_reject(self, reason=False):
        for record in self:
            if record.cutting_order_ids:
                for cutting_order in record.cutting_order_ids:
                    cutting_order.action_reject()
                    
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)

            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'rejected'})
