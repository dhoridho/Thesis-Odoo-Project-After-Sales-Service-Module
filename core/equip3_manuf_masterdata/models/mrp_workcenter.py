from odoo import fields, models, api, _


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _inherit = ['mrp.workcenter', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char('Work Center', related='resource_id.name', store=True, readonly=False, tracking=True)
    location_id = fields.Many2one('stock.location', 'Location', tracking=True)
    location_finished_id = fields.Many2one('stock.location', 'Finished', tracking=True)
    location_rejected_id = fields.Many2one('stock.location', 'Rejected', tracking=True)
    location_byproduct_id = fields.Many2one('stock.location', 'By-Products', tracking=True)

    oh_time = fields.One2many('overhead.time', 'mrp_workcenter_id', string="product")
    ov_material = fields.One2many('overhead.material', 'mrp_wc_id', tracking=True)
    
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                             domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    create_uid = fields.Many2one('res.users', string='Create By', default=lambda self: self.env.user, tracking=True)
    alternative_workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'mrp_workcenter_alternative_rel',
        'workcenter_id',
        'alternative_workcenter_id',
        domain="[('id', '!=', id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        string="Alternative Workcenters", check_company=True,
        help="Alternative workcenters that can be substituted to this one in order to dispatch production", tracking=True
    )
    code = fields.Char('Code', copy=False, required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', required=True, index=True, readonly=True, tracking=True,
        default=lambda self: self.env.company)
    time_efficiency = fields.Float('Time Efficiency', related='resource_id.time_efficiency', default=100, store=True,
                                   readonly=False, tracking=True)
    capacity = fields.Float(
        'Capacity', default=1.0,
        help="Number of pieces that can be produced in parallel. In case the work center has a capacity of 5 and you have to produce 10 units on your work order, the usual operation time will be multiplied by 2.", tracking=True)
    oee_target = fields.Float(string='OEE Target', help="Overall Effective Efficiency Target in percentage", default=90, tracking=True)
    time_start = fields.Float('Time before prod.', help="Time in minutes for the setup.", tracking=True)
    time_stop = fields.Float('Time after prod.', help="Time in minutes for the cleaning.", tracking=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')

    last_finished_date = fields.Datetime(compute='_compute_last_finished_date')

    _sql_constraints = [
        ('unique_code', 'Check(1=1)', 'For the code that is already there, please check!'),
        (
            "unique_code",
            "unique(code)",
            "For the code that is already there, please check!",
        )
    ]

    @api.depends('order_ids', 'order_ids.date_planned_finished')
    def _compute_last_finished_date(self):
        for record in self:
            orders = record.order_ids.filtered(lambda o: o.date_planned_finished)
            last_finished_date = False
            if orders:
                last_finished_date = sorted(orders, key=lambda o: o.date_planned_finished)[-1].date_planned_finished
            record.last_finished_date = last_finished_date

    @api.onchange('location_id')
    def onchange_wc_location(self):
        if self.location_id:
            if not self.location_finished_id:
                self.location_finished_id = self.location_id.id
            if not self.location_rejected_id:
                self.location_rejected_id = self.location_id.id
            if not self.location_byproduct_id:
                self.location_byproduct_id = self.location_id.id

    def _get_first_available(self):
        workcenters = self
        if not workcenters:
            return self.env['mrp.workcenter']
        
        not_blocked_workcenters = workcenters.filtered(lambda w: w.state != 'blocked')

        # all workcenters is blocked
        if not not_blocked_workcenters:
            return workcenters[0]

        # exact 1 workcenter isn't blocked
        if len(not_blocked_workcenters) == 1:
            return not_blocked_workcenters[0]

        available_workcenters = not_blocked_workcenters.filtered(lambda w: w.state == 'available')

        # has available workcenter
        if available_workcenters:
            return available_workcenters[0]
        
        # shortest time waiting
        finish_time = {}
        for workcenter in not_blocked_workcenters:
            sorted_orders = sorted(workcenter.order_ids.filtered(lambda o: o.date_planned_finished), key=lambda w: w.date_planned_finished)
            if not sorted_orders:
                return workcenter
            finish_time[workcenter] = sorted_orders[-1] # last finished order
        return sorted(finish_time.items(), key=lambda o: o[1].date_planned_finished)[0][0] # early finished
