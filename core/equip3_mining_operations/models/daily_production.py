from odoo import models, fields, api, _


class DailyProduction(models.Model):
    _name = 'daily.production'
    _inherit = 'mail.thread'
    _description = 'Daily Production Record'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('daily.production') or _('New')
        return super(DailyProduction, self).create(vals)

    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.daily_production:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mining.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'mdp')
        ], limit=1).id

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
            lines = []
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'mdp_id': record.id,
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

    def _get_default_allowed_operations(self):
        operation_list = []
        if self.env.company.overburden and self.env.ref('equip3_mining_operations.mining_operation_overburden'):
            operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_overburden').id)
        if self.env.company.coal_getting and self.env.ref('equip3_mining_operations.mining_operation_coal_getting'):
            operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_coal_getting').id)
        if self.env.company.hauling and self.env.ref('equip3_mining_operations.mining_operation_hauling'):
            operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_hauling').id)
        if self.env.company.crushing and self.env.ref('equip3_mining_operations.mining_operation_crushing'):
            operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_crushing').id)
        if self.env.company.barging and self.env.ref('equip3_mining_operations.mining_operation_barging'):
            operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_barging').id)
        return [(6, 0, operation_list)]

    def _get_allowed_operations(self):
        for daily_production in self:
            operation_list = []
            if self.env.company.overburden and self.env.ref('equip3_mining_operations.mining_operation_overburden'):
                operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_overburden').id)
            if self.env.company.coal_getting and self.env.ref('equip3_mining_operations.mining_operation_coal_getting'):
                operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_coal_getting').id)
            if self.env.company.hauling and self.env.ref('equip3_mining_operations.mining_operation_hauling'):
                operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_hauling').id)
            if self.env.company.crushing and self.env.ref('equip3_mining_operations.mining_operation_crushing'):
                operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_crushing').id)
            if self.env.company.barging and self.env.ref('equip3_mining_operations.mining_operation_barging'):
                operation_list.append(self.env.ref('equip3_mining_operations.mining_operation_barging').id)
            daily_production.allowed_operation_ids = [(6, 0, operation_list)]

    name = fields.Char('Name', tracking=True)
    mining_site_id = fields.Many2one('mining.site.control', string='Mining Site Name', tracking=True)
    mining_project_id = fields.Many2one('mining.project.control', domain="[('mining_site_id', '=', mining_site_id)]", string='Mining Pit', tracking=True)
    ppic = fields.Many2one('res.users', 'PPIC', tracking=True)
    allowed_operation_ids = fields.Many2many('mining.operations', string='Allowed Operations',
                                             compute='_get_allowed_operations', default=_get_default_allowed_operations)
    operation_id = fields.Many2one('mining.operations','Operations', domain="[('id', 'in', allowed_operation_ids)]")
    operation_name = fields.Char('Selected Operation Name')
    responsible = fields.Char('Responsible', tracking=True)
    operation_tab_id = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], string='State', default='draft', tracking=True)

    state_reject = fields.Selection([
        ('draft', 'Draft'),
        ('rejected', 'Rejected'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
    ])
    assets = fields.Many2one('maintenance.equipment', string='Assets')
    hauling_capacity = fields.Float('Capacity', related='assets.capacity_asset')
    production_date = fields.Datetime('Production Date', tracking=True)
    source_location = fields.Char('Source Location', tracking=True)
    destination_location = fields.Char('Destination Location', tracking=True)
    weight = fields.Char('Weight', tracking=True)
    uom = fields.Many2one(related='company_id.hauling_uom',string='UOM', tracking=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    product_shelter_id = fields.Many2many(comodel_name='product.product', string='Product Shelter')

    # today's changes -----------
    cg_assets = fields.Many2one('maintenance.equipment', string='Assets')
    cg_capacity = fields.Float('Capacity', related='cg_assets.capacity_asset')
    cg_operator = fields.Many2one('res.users', string='Operator')
    operating_hr_from = fields.Datetime(string='Operating Hour')
    operating_hr_to = fields.Datetime(string='To')
    cg_weight = fields.Float(string='Weight')
    cg_uom = fields.Many2one(related='company_id.coal_getting_uom',string='UOM', tracking=True)

    # overburden
    overburden_assets = fields.Many2one('maintenance.equipment', string='Assets')
    overburden_capacity = fields.Float(related='overburden_assets.capacity_asset')
    overburden_operator = fields.Many2one('res.users', string='Operator')
    overburden_hr_from = fields.Datetime(string='Operating Hour', default=fields.Datetime.now)
    overburden_hr_to = fields.Datetime(string='To', default=fields.Datetime.now)
    overburden_weight = fields.Float(string='Weight')
    overburden_uom = fields.Many2one(related='company_id.overburden_uom', string='UOM', tracking=True)
    overburden_location = fields.Many2one('stock.location', string='Location')
    overburden_notes = fields.Char(string='Notes')

    # crushing
    crushing_assets = fields.Many2one('maintenance.equipment', string='Assets')
    crushing_capacity = fields.Float(related='crushing_assets.capacity_asset')
    crushing_hr_from = fields.Datetime(string='Operating Hour', default=fields.Datetime.now)
    crushing_hr_to = fields.Datetime(string='To', default=fields.Datetime.now)
    crushing_uom = fields.Many2one(related='company_id.crushing_uom', string='UOM', tracking=True)
    crushing_waste = fields.Float(string='Waste', default=1)
    crushing_input_product_id = fields.Many2one(comodel_name='product.product', string='Input Product')
    crushing_input_weight = fields.Float(string='Input Weight', default=0)
    crushing_output_product_id = fields.Many2one(comodel_name='product.product', string='Output Product')
    crushing_output_weight = fields.Float(string='Output Product', default=0)
    crushing_output = fields.Float(string='Output Product', default=0)

    # barging
    barging_assets = fields.Many2one('maintenance.equipment', string='Assets')
    barging_capacity = fields.Float(related='barging_assets.capacity_asset')
    barging_capacity_uom = fields.Many2one(related='barging_assets.capacity_asset_uom')
    barging_leave_date = fields.Datetime(string='Leave Date', default=fields.Datetime.now)
    barging_eta = fields.Float(string="ETA")
    barging_arrive_date = fields.Datetime(string='Arrive Date', default=fields.Datetime.now)
    barging_route = fields.Many2one('stock.location', string="Route")
    barging_gross_weight = fields.Float(string='Gross Weight')
    barging_gross_weight_uom = fields.Many2one(related='company_id.barging_uom', string='UOM', tracking=True)
    barging_tare_weight = fields.Float(string='Tare Weight')
    barging_tare_weight_uom = fields.Many2one(related='company_id.barging_uom', string='UOM', tracking=True)
    barging_net_weight = fields.Float(string='Net Weight')
    barging_net_weight_uom = fields.Many2one(related='company_id.barging_uom', string='UOM', tracking=True)

    analytic_group_ids = fields.Many2many(
        comodel_name='account.analytic.tag', 
        domain="[('company_id', '=', company_id)]", 
        string="Analytic Group", 
        readonly=True, 
        states={'draft': [('readonly', False)]}, 
        default=_default_analytic_tag_ids,
        tracking=True)
    
    approval_matrix_id = fields.Many2one(
        comodel_name='mining.approval.matrix', 
        domain="[('matrix_type', '=', 'mdp')]",
        string='Approval Matrix', 
        default=_default_approval_matrix)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='mining.approval.matrix.entry',
        inverse_name='mdp_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    is_matrix_on = fields.Boolean(related='company_id.daily_production')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)

    @api.onchange('mining_site_id', 'operation_id')
    def onchange_mining_site_id(self):
        shelter = []
        self.product_id = None
        self.product_shelter_id = None
        search_prod_mining = self.env['product.mining.site'].search([('mining_site_control_id', '=', self.mining_site_id.id), ('operation_id', '=', self.operation_id.id)])
        if self.mining_site_id and self.operation_id.id == self.env.ref('equip3_mining_operations.mining_operation_overburden').id:
            self.overburden_location = self.mining_site_id.site_location.id
        if self.mining_site_id and self.operation_id:
            if search_prod_mining:
                for prod in search_prod_mining.product_id:
                    shelter.append(prod.id)
                self.product_shelter_id = search_prod_mining.product_id
                self.product_id = shelter[0]

    @api.onchange('operation_id')
    def onchange_operation(self):
        operations = self.env['mining.operations'].search([('name','=','Hauling')])
        self.operation_name = self.operation_id.name
        if self.operation_id == operations:
            self.operation_tab_id = True
        else:
            self.operation_tab_id = False

        if self.mining_site_id and self.operation_id.id == self.env.ref('equip3_mining_operations.mining_operation_overburden').id:
            self.overburden_location = self.mining_site_id.site_location.id

    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.daily_production_wa_notif
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

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancel'
