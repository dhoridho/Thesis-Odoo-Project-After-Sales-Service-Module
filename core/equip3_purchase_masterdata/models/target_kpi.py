from odoo import api, fields, models, _
from datetime import date


class TargetKPI(models.Model):
    _name = 'target.kpi'
    _description = 'Target KPI Purchase'
    _inherit = 'mail.thread'
    _order = 'id desc'
    
    def _default_branch(self):
        return self.env.branch.id

    EDITABLE_STATES = {'draft': [('readonly', False)]}

    name = fields.Char(string='Name', default=lambda self: _(
        '/'), index=True, tracking=True, copy=False, readonly=True)
    purchase_team_id = fields.Many2one(comodel_name='dev.purchase.team', string='Purchase Team', readonly=True,
                                       states=EDITABLE_STATES)
    user_id = fields.Many2one(comodel_name='res.users', string='Purchase Person', required=True, readonly=True,
                              states=EDITABLE_STATES)
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', default=_default_branch, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    target_based_on_ids = fields.Many2many(comodel_name='purchase.target.based.on', string='Target Based on',
                                           required=True, readonly=True, states=EDITABLE_STATES)
    main_target = fields.Float(string='Main Target', readonly=True, states=EDITABLE_STATES)
    current_achievement = fields.Float(string='Current Achievement')
    from_date = fields.Date(string='From Date', required=True, readonly=True, states=EDITABLE_STATES)
    to_date = fields.Date(string='To Date', required=True, readonly=True, states=EDITABLE_STATES)
    target_on = fields.Selection(string='Target Based On',
                                 selection=[('amount', 'Amount Saved'), ('qty', 'Number of Successful Cost Saving'), ],
                                 required=True, readonly=True, states=EDITABLE_STATES, default="amount")
    target_left = fields.Float(string='Target Left', compute="_compute_target_left", store=False)
    kpi_progress = fields.Float(string='KPI Progress', compute="_compute_target_left", store=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('expired', 'Expired'),
        ('cancel', 'Cancel'),
        ('failed', 'Failed'),
        ('succeed', 'Succeed'),
    ], string='State', default="draft")
    select_type = fields.Selection([
        ('all_product', 'All Products'),
        ('categ', 'Product Categories'),
        ('product', 'Products'),
    ], string='Product Based On', default="all_product")
    is_all_product = fields.Boolean("All Products", default=True)
    is_product_category = fields.Boolean("Product Categories")
    is_products = fields.Boolean("Products")
    product_categories = fields.Many2many('product.category', string="Product Category")
    products = fields.Many2many('product.product', string="Products")

    @api.onchange('select_type')
    def onchange_type_product(self):
        for rec in self:
            rec.write({
                'is_all_product': False,
                'is_product_category': False,
                'is_products': False
            })
            if rec.select_type == 'all_product':
                rec.is_all_product = True
            if rec.select_type == 'categ':
                rec.is_product_category = True
            if rec.select_type == 'product':
                rec.is_products = True


    @api.onchange('purchase_team_id')
    def _onchange_purchase_team_id(self):
        domain = []
        if self.purchase_team_id:
            members = self.purchase_team_id.member_ids
            domain = [('id', 'in', members.ids)]
        return {'domain': {'user_id': domain}}

    @api.depends('main_target', 'current_achievement')
    def _compute_target_left(self):
        for i in self:
            i.target_left = i.main_target - i.current_achievement
            if i.main_target:
                i.kpi_progress = 100 * i.current_achievement / i.main_target
            else:
                i.kpi_progress = 0

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.target.kpi') or '/'
        result = super(TargetKPI, self).create(vals)
        return result

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_expired(self):
        self.write({'state': 'expired'})

    def _target_kpi_expire(self):
        today = date.today()
        # target_kpi = self.env['target.kpi'].search([
        #     ('to_date', '<', today),
        #     ('state', '=', 'confirm')
        # ])
        # if target_kpi:
        #     target_kpi.action_expired()

        kpi_ids = self.env['target.kpi'].search([('to_date', '<', today), ('state', '=', 'confirm')])
        if kpi_ids:
            for kpi_rec in kpi_ids:
                if kpi_rec.current_achievement < kpi_rec.main_target:
                    kpi_rec.write({'state': 'failed'})

                elif kpi_rec.current_achievement >= kpi_rec.main_target:
                    kpi_rec.write({'state': 'succeed'})


class PurchaseTargetBasedOn(models.Model):
    _name = 'purchase.target.based.on'
    _description = 'Purchase Target Based on'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
