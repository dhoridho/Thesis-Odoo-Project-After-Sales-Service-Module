from odoo import models, fields, api, _


class OutletOrder(models.Model):
    _name = 'kitchen.outlet.order'
    _description = 'Outlet Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, tracking=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True, tracking=True)
    outlet_warehouse_id = fields.Many2one('stock.warehouse', string='Outlet Warehouse', required=True, tracking=True)
    outlet_location_id = fields.Many2one('stock.location', string='Outlet Destination', required=True, tracking=True)
    date_scheduled = fields.Datetime(string='Scheduled Date', required=True, default=fields.Date.today, readonly=True, tracking=True)

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, required=True, tracking=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, required=True, tracking=True)
    analytic_group_ids = fields.Many2many(
        comodel_name='account.analytic.tag', 
        domain="[('company_id', '=', company_id)]", 
        string="Analytic Group", 
        readonly=True, 
        states={'draft': [('readonly', False)]}, 
        default=_default_analytic_tag_ids,
        tracking=True)

    create_uid = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True)

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('waiting', 'Waiting'),
            ('ready', 'Ready'),
            ('done', 'Done')
        ],
        string='Status',
        default='draft'
    )

    move_ids = fields.One2many('stock.move', 'kitchen_outlet_id', string='Operations')
