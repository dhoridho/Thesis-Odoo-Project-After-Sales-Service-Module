import json
import calendar

from odoo import api, fields, models, _
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import pytz



class ProcurementPlanning(models.TransientModel):
    _name = 'procurement.planning'
    _description = 'Procurement Planning'

    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse')
    start_date = fields.Date('Start Date', default=lambda self: fields.Date.context_today(self) + timedelta(days=-365))
    end_date = fields.Date('End Date', default=lambda self: fields.Date.context_today(self))
    lead_time = fields.Integer('Lead Time')
    product_category_ids = fields.Many2many(
        comodel_name='product.category', string='Product Category')
    product_ids = fields.Many2many(
        comodel_name='product.product', string='Product')
    suggest_stock_period = fields.Integer(default=30, string='Suggested Stock Period')

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date_end_date(self):
        today = fields.Date.context_today(self)
        if self.start_date > today:
            raise ValidationError(_('You cannot insert start date more than today'))
        if self.end_date > today:
            raise ValidationError(_('You cannot insert end date more than today'))


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
            where_domain_stock_warehouse += "warehouse_id in (%s)" % str(self.warehouse_id.id)
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
            where_domain_stock_warehouse += "and swo.product_id in %s" % str(products)
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


        if self.lead_time:
            lead_time = self.lead_time
        else:
            lead_time = 0

        if self.suggest_stock_period:
            suggest_stock_period = self.suggest_stock_period
        else:
            suggest_stock_period = 0

        query = f"""
        select sq.product_id as product_id,
                sum(sq.quantity - sq.reserved_quantity) as quantity,
                move_out.product_uom_qty as sold_quantity,
                case when
                    sum(move_out.product_uom_qty) <>  0 then
                        (sum(move_out.product_uom_qty) / {difference_time})
                    else 0 end as run_rate,

                case when
                    sum(move_out.product_uom_qty) >= 1 or
                    sum(move_out.product_uom_qty) <> 0 and
                    (sum(move_out.product_uom_qty) /  {difference_time}) > 0 then
                        floor((sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time})))
                    else 0 end as stock_days,

                case
                    when
                        floor((sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time}))) >= 99999999
                    then
                        current_date + interval '99999999 days'
                    when
						sum(move_out.product_uom_qty) >= 1 or
						sum(move_out.product_uom_qty) <> 0 and
						(sum(move_out.product_uom_qty) /  {difference_time}) > 0 and
						floor((sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time}))) <= 99999999
					then
						current_date + (floor((sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time}))) )::integer
                    else
                        current_date end as period,

                case
					when
                    	sum(stock_warehouse.product_min_qty) > 1 and
						floor(sum((sq.quantity - sq.reserved_quantity) - (stock_warehouse.product_min_qty)) / (sum(move_out.product_uom_qty) / {difference_time})) - {lead_time} <= 99999999
					then
                       	current_date + (floor(sum((sq.quantity - sq.reserved_quantity) -
										 (stock_warehouse.product_min_qty))
										 / (sum(move_out.product_uom_qty) / {difference_time})
									   ) - {lead_time})::integer
					when
                    	sum(stock_warehouse.product_min_qty) > 1 and
						sum((sq.quantity - sq.reserved_quantity) - (stock_warehouse.product_min_qty)) / (sum(move_out.product_uom_qty) / {difference_time}) - {lead_time} >= 99999999
					then
						current_date + interval '99999999 days'

					when
						(sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time})) - {lead_time} >= 99999999
					then
                    	current_date + interval '99999999 days'
					when
						floor((sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time}))) - {lead_time} <= 99999999
					then
                        current_date + (floor((sum(sq.quantity - sq.reserved_quantity) / (sum(move_out.product_uom_qty) /  {difference_time}))) - {lead_time})::integer
                    else
                        current_date end as next_order,

                case when
                     	sum(stock_warehouse.product_min_qty) is null
                    then
						floor((sum(move_out.product_uom_qty) / {difference_time}) * {suggest_stock_period})
                    when
						sum(stock_warehouse.product_min_qty) > 1
                    then
                        sum(stock_warehouse.product_max_qty - stock_warehouse.product_min_qty)

					end as stock_order
        from stock_quant as sq
        left join product_product as pp ON sq.product_id = pp.id
        left join product_template as pt ON pt.id = pp.product_tmpl_id
        left join product_category as pc ON pt.categ_id = pp.id
        left join stock_location as sl ON sq.location_id = sl.id
        left join (select   sm.product_id,
                            sum(sm.product_uom_qty) as product_uom_qty
                    from    stock_move as sm
                            left join stock_picking_type as spt ON sm.picking_type_id = spt.id
                            left join product_product as pp ON sm.product_id = pp.id
                            left join product_template as pt ON pt.id = pp.product_tmpl_id
                            left join product_category as pc ON pt.categ_id = pp.id
                    where spt.code = 'outgoing' {where_domain_out}
                    group by sm.product_id)
            as move_out ON move_out.product_id = sq.product_id
        left join ( select swo.product_id,
				  			swo.product_min_qty,
                            swo.product_max_qty
				 	from stock_warehouse_orderpoint as swo
                        left join product_product as pp ON swo.product_id = pp.id
                        left join product_template as pt ON pt.id = pp.product_tmpl_id
                        left join product_category as pc ON pt.categ_id = pp.id
				  where {where_domain_stock_warehouse})
            as stock_warehouse ON stock_warehouse.product_id = sq.product_id
        where sl.usage = 'internal' {where_domain}
        group by sq.product_id,move_out.product_uom_qty
        """
        print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data

    def get_product_stock_movements(self):
        self.ensure_one()

        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        companies = self.env['res.company'].search([('id', 'child_of', self.company_id.ids)])
        company_ids = set(companies.ids) or {}

        warehouses = self.warehouse_id and set(self.warehouse_id.ids) or {}

        today = fields.Date.today()
        product_wise_data = {}
        for month in range(11, -1, -1):
            previous_month = today - relativedelta(months=month)
            start_date = previous_month.replace(day=1)
            end_day_of_the_month = calendar.monthrange(start_date.year, start_date.month)[1]
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
        return self.env['procurement.planning.line'].create(data)

    def view_data(self):
        planning_data = self.get_procurement_planning_data()
        stock_data = self.get_product_stock_movements()

        warehouse_id = self.warehouse_id.id
        for data in planning_data:
            product_id = data.get('product_id', False)
            data.update({'stock_data': json.dumps(stock_data.get(product_id, '{}'), default=str)})

        self.create_data([{'wizard_id': self.id, **data} for data in planning_data])
        return {
            'type': 'ir.actions.act_window',
            'domain': [('wizard_id', '=', self.id)],
            'name': 'Procurement Planning',
            'view_mode': 'tree,form',
            'res_model': 'procurement.planning.line',
            'context': {'group_by': 'next_order:day', 'default_order_next_order': 'next_order'},
            'target': 'current',
        }


class ProcurementPlanningLine(models.TransientModel):
    _name = 'procurement.planning.line'
    _description = 'Procurement Planning Line'

    product_id = fields.Many2one("product.product", "Product")
    quantity = fields.Float("Available Quantity")
    sold_quantity = fields.Float("Sold Quantity")
    run_rate = fields.Float("Run Rate",
                            help="Run rate is an average number of how many products are sold in a day.\n Formula = Sold Quantity : Period Start Date until End Date")
    stock_days = fields.Float("In Stock Days")
    combined_field = fields.Char(
        string='In Stock Days String', compute='_compute_combined_field', store=True,
        help="IN STOCK DAYS is an estimate of how many days the product quantity will be sufficient\n Formula : Availabe Quantity : Run Rate ")
    period = fields.Date("Sufficient Holding Period",
                        help="SUFFICIENT HOLDING PERIOD is until what date the product will be sufficient \n Formula : Current Days + In Stock Day")
    next_order = fields.Date("Suggested Date to Order",
                            help="SUGGESTED DATE TO ORDER is the proposed date when the product will be ordered\n Formula = (Available Quantity(quantity) - Min Reordering Rules(product_min_qty) : Run Rate(run_rate) + Current date )")
    stock_order = fields.Integer("Stock To Order",
                            help="STOCK TO ORDER is a suggestion for the quantity of product that must be ordered\n Formula = Suggested Stock Period x Run Rate or Max Quantity - Min Quantity")
    wizard_id = fields.Many2one("procurement.planning")

    has_reordering_rules = fields.Boolean(compute="_compute_has_reordering_rules")
    stock_data = fields.Text()

    @api.depends('stock_days')
    def _compute_combined_field(self):
        for record in self:
            record.combined_field = f"{record.stock_days} Days"

    @api.depends('product_id', 'wizard_id')
    def _compute_has_reordering_rules(self):
        ReorderingRule = self.env['stock.warehouse.orderpoint']
        rules_dict = {}
        for record in self:
            product_id = record.product_id and record.product_id.id or False
            warehouse_id = record.wizard_id and record.wizard_id.warehouse_id.id or False
            key = (product_id, warehouse_id)
            if key not in rules_dict:
                rules_dict[key] = ReorderingRule.search_count([('product_id', '=', product_id), ('warehouse_id', '=', warehouse_id)]) > 0
            record.has_reordering_rules = rules_dict[key]

    def action_view_graph(self):
        self.ensure_one()
        stock_data = json.loads(self.stock_data)
        today = fields.Date.today()
        last_date_of_the_month = calendar.monthrange(today.year, today.month)[1]
        stock_data_values = stock_data.values()
        data = {
            'product_id': self.product_id.id,
            'warehouse_id': self.wizard_id.warehouse_id.id,
            'closing': {month: o['closing'] for month, o in stock_data.items()},
            'sales': sum([o['sales'] for o in stock_data_values]) if stock_data_values else 0.0,
            'day_left': last_date_of_the_month - today.day,
            'available_qty': self.quantity
        }
        return {
            'name': 'Procurement Planning Graph',
            'type': 'ir.actions.client',
            'tag': 'procurement_planning_graph',
            'target': 'new',
            'context': {
                'line_data': data
            }
        }
