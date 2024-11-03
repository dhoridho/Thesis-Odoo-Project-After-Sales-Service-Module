import json
import calendar

from odoo import api, fields, models, _
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import pytz


class ProcurementPlanningModel(models.Model):
    _name = 'procurement.planning.model'
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']
    _order = 'id desc'
    _description = 'Procurement Planning Model'

    @api.model
    def _get_default_analytic(self):
        analytic_priority_ids = self.env['analytic.priority'].search(
            [], order="priority")
        for analytic_priority in analytic_priority_ids:
            self.env.user.analytic_tag_ids
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                analytic_tags_ids = self.env['account.analytic.tag'].search(
                    [('id', 'in', self.env.user.analytic_tag_ids.ids), ('company_id', '=', self.env.user.company_id.id)])
                return analytic_tags_ids
            elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                analytic_tags_ids = self.env['account.analytic.tag'].search(
                    [('id', 'in', self.env.user.branch_id.analytic_tag_ids.ids), ('company_id', '=', self.env.user.company_id.id)])
                return analytic_tags_ids

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id', '=', self.env.company.id)]

    @api.model
    def _warehouse_domain(self):
        return [('company_id', '=', self.env.company.id)]

    name = fields.Char(string='Reference', default='New', copy=False)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse', tracking=True, domain=_warehouse_domain)
    start_date = fields.Date('Start Date', default=lambda self: fields.Date.context_today(
        self) + timedelta(days=-365))
    end_date = fields.Date(
        'End Date', default=lambda self: fields.Date.context_today(self))
    lead_time = fields.Integer('Lead Time')
    product_category_ids = fields.Many2many(
        comodel_name='product.category', string='Product Category')
    product_ids = fields.Many2many(
        comodel_name='product.product', string='Product')
    suggest_stock_period = fields.Integer(
        default=30, string='Suggested Stock Period')
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('confirm', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Closed')],
        default='draft', tracking=True)
    analytic_group_ids = fields.Many2many(
        comodel_name='account.analytic.tag', string='Analytic Group', domain="[('company_id', '=', company_id)]", required=True, default=_get_default_analytic)
    procurement_line = fields.One2many(comodel_name='procurement.planning.model.line',
                                       inverse_name='procurement_id', string='Procurement Planning Line')
    rfq_count = fields.Integer(string='Rfq Count', compute='compute_rfq_count')
    pr_count = fields.Integer(string='Pr Count', compute='compute_pr_count')
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch',
                                required=True, tracking=True, domain=_domain_branch)
    is_multi_leadtime = fields.Boolean(string='Is Multi Lead Time')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',
                       ('branch_id', '=', False),
                       ('branch_id', 'in', self.env.branches.ids),
                       ('company_id', 'in', self.env.companies.ids)])
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'procurement.planning.model') or _('New')
        return super(ProcurementPlanningModel, self).create(vals)

    def action_simulate(self):
        planning_data = self.get_procurement_planning_data()
        stock_data = self.get_product_stock_movements()

        for data in planning_data:
            product_id = data.get('product_id', False)
            data.update({'stock_data': json.dumps(
                stock_data.get(product_id, '{}'), default=str)})

        self.procurement_line.unlink()
        self.create_data([{'procurement_id': self.id, **data}
                         for data in planning_data])
        self.state = 'ready' if self.state == 'draft' else 'ready'

    def action_confirm(self):
        self.state = 'confirm'
        for line in self.procurement_line.filtered(lambda l: l.stock_order > 0 and l.request_to_order <= 0):
            line.request_to_order = line.stock_order

    def action_done(self):
        self.state = 'done'

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date_end_date(self):
        today = fields.Date.context_today(self)
        if self.start_date > today:
            raise ValidationError(
                _('You cannot insert start date more than today'))
        if self.end_date > today:
            raise ValidationError(
                _('You cannot insert end date more than today'))

    @api.onchange('start_date')
    def _onchange_start_date(self):
        today = fields.Date.context_today(self)
        if self.start_date:
            self.end_date = self.start_date + timedelta(days=365)
            if self.end_date > today:
                self.end_date = today

    def get_procurement_planning_data(self):
        difference_time = (self.end_date - self.start_date).days
        where_domain = ""
        where_domain_stock_warehouse = ""

        currenttimezone = pytz.timezone(self.env.context.get('tz'))
        if currenttimezone:
            user_datetime = datetime.now(currenttimezone)
            timezone_plus_or_minus = user_datetime.strftime('%z')[0]
            timezone_str = user_datetime.strftime('%z')[1:3]

        if not currenttimezone:
            raise ValidationError(_('You need to fill timezone in this User'))

        if difference_time:
            where_domain_out = "and sm.date %s interval '%s hour' between '%s 00:00:00' and '%s 23:59:59'" % (
                timezone_plus_or_minus, timezone_str, self.start_date, self.end_date)

        if self.warehouse_id:
            location = self.env['stock.location'].search(
                [('warehouse_id', '=', self.warehouse_id.id),
                 ('usage', '=', 'internal')])
            location_ids = tuple(location.ids)
            where_domain_stock_warehouse += "warehouse_id in (%s)" % str(
                self.warehouse_id.id)
            where_domain += "and sq.location_id in %s" % str(location_ids)
            where_domain_out += "and sm.location_id in %s" % str(location_ids)
        else:
            location_ids = set()

        # if product ids filled and product_category ids filled
        if self.product_ids and self.product_category_ids:
            if len(self.product_ids) == 1:
                products = self.product_ids.ids
                products.append(0)
                products = tuple(products)
            elif len(self.product_ids) > 1:
                products = tuple(self.product_ids.ids)

            if len(self.product_category_ids) == 1:
                product_category_ids = self.product_category_ids.ids
                product_category_ids.append(0)
                product_category_ids = tuple(product_category_ids)
            elif len(self.product_category_ids) > 1:
                product_category_ids = tuple(self.product_category_ids.ids)

            where_domain += "and pt.id in %s or sq.product_id in %s" % (str(
                product_category_ids), str(products))
            where_domain_out += "and pt.id in %s or sm.product_id in %s" % (str(
                product_category_ids), str(products))
            where_domain_stock_warehouse += "and pt.id in %s or swo.product_id in %s" % (str(
                product_category_ids), str(products))

        # if product ids filled and product_category ids not filled
        if self.product_ids and not self.product_category_ids:
            if len(self.product_ids) == 1:
                products = self.product_ids.ids
                products.append(0)
                products = tuple(products)
            elif len(self.product_ids) > 1:
                products = tuple(self.product_ids.ids)
            where_domain += "and sq.product_id in %s" % str(products)
            where_domain_out += "and sm.product_id in %s" % str(products)
            where_domain_stock_warehouse += "and swo.product_id in %s" % str(
                products)
        else:
            products = set()

        # if product ids not filled and product_category ids filled
        if self.product_category_ids and not self.product_ids:
            if len(self.product_category_ids) == 1:
                product_category_ids = self.product_category_ids.ids
                product_category_ids.append(0)
                product_category_ids = tuple(product_category_ids)
            elif len(self.product_category_ids) > 1:
                product_category_ids = tuple(self.product_category_ids.ids)
            where_domain += "and pt.categ_id in %s" % str(
                product_category_ids)
            where_domain_out += "and pt.categ_id in %s" % str(
                product_category_ids)
            where_domain_stock_warehouse += "and pt.categ_id in %s" % str(
                product_category_ids)
        else:
            product_category_ids = set()

        lead_time = self.lead_time or 0
        suggest_stock_period = self.suggest_stock_period or 0

        query = f"""
        SELECT
            sq.product_id AS product_id,
            SUM(sq.quantity - sq.reserved_quantity) AS quantity,
            COALESCE(move_out.product_uom_qty, 0) AS sold_quantity,
            CASE
                WHEN (move_out.product_uom_qty) <> 0 
                THEN
                    ROUND(((move_out.product_uom_qty) / {difference_time}),2)
                ELSE
                    0
            END AS run_rate,

            CASE
                WHEN SUM(move_out.product_uom_qty) <> 0 AND ROUND(((move_out.product_uom_qty) / {difference_time}),2) <> 0
                THEN
                    SUM(sq.quantity - sq.reserved_quantity) / ROUND(((move_out.product_uom_qty) / {difference_time}), 2)
                ELSE
                    0
            END AS stock_days,

            CASE
                WHEN (move_out.product_uom_qty) <> 0 AND FLOOR(SUM(sq.quantity - sq.reserved_quantity) / NULLIF(((move_out.product_uom_qty) / {difference_time}), 0)) >= 99999999 THEN
                    CURRENT_DATE + INTERVAL '99999999 days'
                WHEN (move_out.product_uom_qty) <> 0 THEN
                    CURRENT_DATE + (FLOOR(SUM(sq.quantity - sq.reserved_quantity) / NULLIF(((move_out.product_uom_qty) / {difference_time}), 0)))::INTEGER
                ELSE
                    CURRENT_DATE
            END AS period,

            CASE
                WHEN (move_out.product_uom_qty) <> 0 AND FLOOR(SUM(sq.quantity - sq.reserved_quantity) / NULLIF(((move_out.product_uom_qty) / {difference_time}), 0)) >= 99999999 THEN
                    CURRENT_DATE + INTERVAL '99999999 days'
                WHEN (move_out.product_uom_qty) <> 0 THEN
                    (CURRENT_DATE + (FLOOR(SUM(sq.quantity - sq.reserved_quantity) / NULLIF(((move_out.product_uom_qty) / {difference_time}), 0)))::INTEGER) - INTERVAL '{lead_time} days'
                ELSE
                    CURRENT_DATE
            END AS next_order,
            
            CASE
                WHEN {suggest_stock_period} - 
                    (CASE
                        WHEN (move_out.product_uom_qty) <> 0 AND ROUND((move_out.product_uom_qty) / {difference_time}, 2) <> 0
                        THEN SUM(sq.quantity - sq.reserved_quantity) / ROUND((move_out.product_uom_qty) / {difference_time}, 2)
                        ELSE 0
                    END) > 0
                THEN
                    ({suggest_stock_period} - 
                    (CASE
                        WHEN (move_out.product_uom_qty) <> 0 AND ROUND((move_out.product_uom_qty) / {difference_time}, 2) <> 0
                        THEN SUM(sq.quantity - sq.reserved_quantity) / ROUND((move_out.product_uom_qty) / {difference_time}, 2)
                        ELSE 0
                    END)) * 
                    (CASE
                        WHEN (move_out.product_uom_qty) <> 0 
                        THEN ROUND((move_out.product_uom_qty) / {difference_time}, 2)
                        ELSE 0
                    END)
                ELSE 0
            END AS stock_order,

            pt.uom_id

        FROM
            stock_quant AS sq
        LEFT JOIN
            product_product AS pp ON sq.product_id = pp.id
        LEFT JOIN
            product_template AS pt ON pt.id = pp.product_tmpl_id
        LEFT JOIN
            product_category AS pc ON pt.categ_id = pp.id
        LEFT JOIN
            stock_location AS sl ON sq.location_id = sl.id
        LEFT JOIN
            (SELECT sm.product_id, SUM(sm.product_uom_qty) AS product_uom_qty
            FROM stock_move AS sm
            LEFT JOIN stock_picking_type AS spt ON sm.picking_type_id = spt.id
            LEFT JOIN product_product AS pp ON sm.product_id = pp.id
            LEFT JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category AS pc ON pt.categ_id = pp.id
            WHERE spt.code = 'outgoing' and sm.state = 'done' {where_domain_out}
            GROUP BY sm.product_id) AS move_out ON move_out.product_id = sq.product_id
        LEFT JOIN
            (SELECT swo.product_id, swo.product_min_qty, swo.product_max_qty
            FROM stock_warehouse_orderpoint AS swo
            LEFT JOIN product_product AS pp ON swo.product_id = pp.id
            LEFT JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN product_category AS pc ON pt.categ_id = pp.id
            WHERE {where_domain_stock_warehouse}) AS stock_warehouse ON stock_warehouse.product_id = sq.product_id
        WHERE
            sl.usage = 'internal' {where_domain}
        GROUP BY
            sq.product_id, move_out.product_uom_qty, pt.uom_id
        """
        # print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data

    def get_product_stock_movements(self):
        self.ensure_one()

        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search(
                [('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        companies = self.env['res.company'].search(
            [('id', 'child_of', self.company_id.ids)])
        company_ids = set(companies.ids) or {}

        warehouses = self.warehouse_id and set(self.warehouse_id.ids) or {}

        today = fields.Date.today()
        product_wise_data = {}
        for month in range(11, -1, -1):
            previous_month = today - relativedelta(months=month)
            start_date = previous_month.replace(day=1)
            end_day_of_the_month = calendar.monthrange(
                start_date.year, start_date.month)[1]
            end_date = previous_month.replace(day=end_day_of_the_month)

            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            query = "SELECT * FROM get_products_stock_movements('%s','%s','%s','%s','%s','%s')" % (
                company_ids, products, category_ids, warehouses, start_date_str, end_date_str)

            self._cr.execute(query)

            for data in self._cr.dictfetchall():
                product_id = data.get('product_id', False)
                if product_id in product_wise_data:
                    if month in product_wise_data[product_id]:
                        product_wise_data[product_id][month].update({
                            'closing': product_wise_data[product_id][month]['closing'] + data.get('closing', 0.0),
                            'sales': product_wise_data[product_id][month]['sales'] + data.get('sales', 0.0),
                        })
                    else:
                        product_wise_data[product_id][month] = {
                            'closing': data.get('closing', 0.0),
                            'sales': data.get('sales', 0.0),
                        }
                else:
                    product_wise_data[product_id] = {month: {
                        'closing': data.get('closing', 0.0),
                        'sales': data.get('sales', 0.0),
                    }}
        return product_wise_data

    def create_data(self, data):
        return self.env['procurement.planning.model.line'].create(data)

    def create_purchase_request(self):
        self.ensure_one()

        line_ids = [
            (0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.request_to_order - line.quantity_ordered,
                'product_uom_id': line.uom_id.id,
                'analytic_account_group_ids': [(6, 0, self.analytic_group_ids.ids)]
            }) for line in self.procurement_line if line.request_to_order > 0
        ]

        ctx = {
            'default_search_default_requested_by': self.env.user.id,
            'goods_order': 1,
        }

        pr_vals = {
            'procurement_planning_id': self.id,
            'branch_id': self.branch_id.id,
            'is_goods_orders': True,
            'is_single_request_date': True,
            'is_single_delivery_destination': True,
            'analytic_account_group_ids': [(6, 0, self.analytic_group_ids.ids)],
            'destination_warehouse': self.warehouse_id.id,
            'line_ids': line_ids
        }

        pr = self.env['purchase.request'].with_context(ctx).create(pr_vals)

        return {
            'name': _("Purchase Request"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_inventory_purchase_operation.purchase_request_inventory_control').id,
            'res_model': 'purchase.request',
            'type': 'ir.actions.act_window',
            'res_id': pr.id,
            'target': 'current',
        }

    def create_rfq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create RFQ',
            'res_model': 'procurement.rfq.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def compute_rfq_count(self):
        self.rfq_count = self.env['purchase.order'].search_count(
            [('procurement_planning_id', '=', self.id)])

    def compute_pr_count(self):
        self.pr_count = self.env['purchase.request'].search_count(
            [('procurement_planning_id', '=', self.id)])

    def action_view_pr(self):
        self.ensure_one()
        return {
            'name': _('Purchase Request'),
            'res_model': 'purchase.request',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (self.env.ref('equip3_inventory_purchase_operation.purchase_request_inventory_control').id, 'form')],
            'domain': [('procurement_planning_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def action_view_rfq(self):
        self.ensure_one()
        return {
            'name': _('RFQ'),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (self.env.ref('equip3_inventory_purchase_operation.purchase_order_inventory_control').id, 'form')],
            'domain': [('procurement_planning_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }


class ProcurementPlanningLine(models.Model):
    _name = 'procurement.planning.model.line'
    _description = 'Procurement Planning Model Line'

    product_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    quantity = fields.Float("Available Quantity")
    sold_quantity = fields.Float("Outgoing Quantity")
    run_rate = fields.Float(
        "Run Rate", help="Run rate is an average number of how many products are sold in a day.\n Formula = Sold Quantity : Period Start Date until End Date")
    stock_days = fields.Float("In Stock Days")
    combined_field = fields.Char(string='In Stock Days String', compute='_compute_combined_field', store=True,
                                 help="IN STOCK DAYS is an estimate of how many days the product quantity will be sufficient\n Formula : Availabe Quantity : Run Rate ")
    period = fields.Date("Sufficient Holding Period",
                         help="SUFFICIENT HOLDING PERIOD is until what date the product will be sufficient \n Formula : Current Days + In Stock Day")
    next_order = fields.Date("Suggested Date to Order",
                             help="SUGGESTED DATE TO ORDER is the proposed date when the product will be ordered\n Formula = (Available Quantity(quantity) - Min Reordering Rules(product_min_qty) : Run Rate(run_rate) + Current date )")
    stock_order = fields.Float("Stock To Order",
                               help="STOCK TO ORDER is a suggestion for the quantity of product that must be ordered\n Formula = Suggested Stock Period x Run Rate or Max Quantity - Min Quantity")
    procurement_id = fields.Many2one(
        comodel_name='procurement.planning.model', string='Procurement Planning', ondelete='cascade')
    has_reordering_rules = fields.Boolean(
        compute="_compute_has_reordering_rules")
    stock_data = fields.Text()
    request_to_order = fields.Float(string='Request To Order')
    quantity_ordered = fields.Float(string='Quantity Ordered')
    quantity_received = fields.Float(string='Quantity Received')
    fulfillment = fields.Char(string='Fulfillment',
                              compute='_compute_fulfillment')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM')
    lead_time = fields.Integer(string='Lead Time')

    @api.depends('product_id', 'procurement_id')
    def _compute_has_reordering_rules(self):
        ReorderingRule = self.env['stock.warehouse.orderpoint']
        rules_dict = {}
        for record in self:
            product_id = record.product_id and record.product_id.id or False
            warehouse_id = record.procurement_id and record.procurement_id.warehouse_id.id or False
            key = (product_id, warehouse_id)
            if key not in rules_dict:
                rules_dict[key] = ReorderingRule.search_count(
                    [('product_id', '=', product_id), ('warehouse_id', '=', warehouse_id)]) > 0
            record.has_reordering_rules = rules_dict[key]

    @api.depends('quantity_ordered', 'request_to_order')
    def _compute_fulfillment(self):
        for record in self:
            if record.request_to_order <= 0:
                record.fulfillment = '0 %'
            else:
                result = (record.quantity_ordered /
                          record.request_to_order) * 100
                record.fulfillment = f'{result:.0f} %'

    @api.onchange('lead_time')
    def _onchange_lead_time(self):
        for record in self:
            if record.lead_time and record.next_order:
                # store the original next_order date if not already stored
                if not record._origin.next_order:
                    record._origin.next_order = record.next_order

                record.next_order = record._origin.next_order - relativedelta(days=record.lead_time)
