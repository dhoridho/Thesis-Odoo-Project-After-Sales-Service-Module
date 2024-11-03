import json
from odoo import models, fields, api, tools, _
from dateutil.relativedelta import relativedelta
from collections import defaultdict


class MovingPlanCostReport(models.Model):
    _name = 'moving.plan.cost.report'
    _description = 'Moving Production Cost Report Plan'
    _auto = False
    _rec_name = 'bom_id'

    bom_id = fields.Many2one('mrp.bom', string='Bill of Material')
    product_id = fields.Many2one('product.product', string='Product')
    last_production_date = fields.Date(string='Last Production Date')
    last_production_id = fields.Many2one('mrp.production', string='Last Production Order')
    production_ids = fields.Many2many('mrp.production', string='Production Orders', compute='_compute_productions')
    plan_ids = fields.Many2many('mrp.plan', string='Production Plans', compute='_compute_productions')
    last_cost_per_uom = fields.Monetary(string='Last Cost Per UoM', compute='_compute_last_cost_per_uom')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    last_cost_per_secondary_uom = fields.Monetary(string='Last Cost Per Secondary UoM', compute='_compute_last_cost_per_secondary_uom')
    secondary_uom_id = fields.Many2one('uom.uom', string='Secondary UoM')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    report_data = fields.Text(compute='_compute_report_data')

    date_from = fields.Date(string='Date From', compute='_compute_date')
    date_to = fields.Date(string='Date To', compute='_compute_date')

    @api.depends('last_production_id')
    def _compute_last_cost_per_uom(self):
        for record in self:
            svls = record.last_production_id.move_finished_ids.filtered(lambda o: not o.byproduct_id).stock_valuation_layer_ids
            record.last_cost_per_uom = sum(svls.mapped('value'))

    @api.depends('uom_id', 'secondary_uom_id', 'last_cost_per_uom')
    def _compute_last_cost_per_secondary_uom(self):
        for record in self:
            cost = 0.0
            uom_id = record.uom_id
            secondary_uom_id = record.secondary_uom_id
            if uom_id and secondary_uom_id and uom_id.category_id == secondary_uom_id.category_id:
                cost = uom_id._compute_price(record.last_cost_per_uom, secondary_uom_id)
            record.last_cost_per_secondary_uom = cost

    @api.depends('bom_id', 'date_from', 'date_to')
    def _compute_productions(self):
        Production = self.env['mrp.production']
        for record in self:
            production_ids = Production.search([
                ('bom_id', '=', record.bom_id.id), 
                ('state', '=', 'done'), 
                ('date_finished', '>=', record.date_from), 
                ('date_finished', '<=', record.date_to),
                ('mrp_plan_id', '!=', False),
                ('mrp_plan_id.state', '=', 'done'),
                ('mrp_plan_id.date_finished', '!=', False)
            ])
            record.production_ids = [(6, 0, production_ids.ids)]
            record.plan_ids = [(6, 0, production_ids.mapped('mrp_plan_id').ids)]

    @api.depends_context('date_from', 'date_to')
    def _compute_date(self):
        today = fields.Date.today()
        self.date_from = self.env.context.get('date_from', today - relativedelta(days=30))
        self.date_to = self.env.context.get('date_to', today)

    @api.depends('bom_id', 'production_ids', 'plan_ids')
    def _compute_report_data(self):
        def _assign_cost_status(costs):
            for i, current_cost in enumerate(costs):
                status = False
                difference = 0.0
                if i > 0:
                    previous_cost = costs[i - 1]
                    if current_cost['value'] < previous_cost['value']:
                        status = 'down'
                        difference = current_cost['value'] - previous_cost['value']
                    elif current_cost['value'] > previous_cost['value']:
                        status = 'up'
                        difference = current_cost['value'] - previous_cost['value']
                current_cost.update({'status': status, 'difference': difference})
            costs.reverse()

        def get_moves(group, plan_orders, bom, level=1):
            orders = plan_orders.filtered(lambda o: o.bom_id == bom)
            for order in orders:
                for move in order.move_raw_ids:
                    product = move.product_id
                    bom_line = move.bom_line_id
                    group[(product, bom_line, level)] |= move
                    if bom_line.child_bom_id:
                        get_moves(group, plan_orders, bom_line.child_bom_id, level=level+1)
            return group

        for record in self:
            bom = record.bom_id or self.env['mrp.bom']
            bom_product = bom.product_tmpl_id
            bom_line_ids = bom.bom_line_ids.ids

            secondary_uom = bom_product.secondary_uom_id
            primary_uom = bom_product.uom_id
            sorted_plan_ids = record.plan_ids.sorted(key=lambda o: o.date_finished)

            group = defaultdict(lambda: self.env['stock.move'])
            for plan in sorted_plan_ids:
                group = get_moves(group, plan.mrp_order_ids, bom)
            
            data = {
                'plans': [],
                'bom_uom': {
                    'uom': bom.product_uom_id.display_name,
                    'product': bom_product.display_name,
                    'quantity': '%s %s' % (bom.product_qty, bom.product_uom_id.display_name),
                    'cost': []
                },
                'secondary_uom': {
                    'uom': secondary_uom.display_name,
                    'product': bom_product.display_name,
                    'quantity': '1.0 %s' % secondary_uom.display_name,
                    'cost': []
                },
                'primary_uom': {
                    'uom': primary_uom.display_name,
                    'product': bom_product.display_name,
                    'quantity': '1.0 %s' % primary_uom.display_name,
                    'cost': []
                },
                'materials': [{
                    'product_id': {'id': product.id, 'display_name': product.display_name},
                    'bom_line_id': {'id': bom_line.id, 'display_name': bom_line.display_name},
                    'uom_id': {'id': product.uom_id.id, 'display_name': product.uom_id.display_name},
                    'product_qty': sum(move.product_qty for move in moves),
                    'level': level,
                    'moves': moves,
                    'cost': []
                } for (product, bom_line, level), moves in group.items()]
            }

            for plan in sorted_plan_ids:
                plan_orders = plan.mrp_order_ids
                
                productions = plan_orders.filtered(lambda o: o.bom_id == bom)
                production = productions and productions[0] or self.env['mrp.production']
                production_uom = production.product_uom_id
                value = abs(sum(production.move_finished_ids.filtered(lambda m: not m.byproduct_id).stock_valuation_layer_ids.mapped('value')))

                data['bom_uom']['cost'] += [{'value': value, 'order': {'id': production.id, 'display_name': production.display_name}}]
                data['secondary_uom']['cost'] += [{'value': production_uom._compute_price(value / production.product_qty, secondary_uom) if secondary_uom else 0.0}]
                data['primary_uom']['cost'] += [{'value': production_uom._compute_price(value / production.product_qty, primary_uom)}]
                
                for material in data['materials']:
                    product_id = material['product_id']['id']
                    bom_line_id = material['bom_line_id']['id']
                    bom_line = self.env['mrp.bom.line'].browse(bom_line_id)
                    moves = material['moves'].filtered(lambda o: o.mrp_plan_id == plan)
                    value = abs(sum(moves.stock_valuation_layer_ids.mapped('value')))
                    quantity = abs(sum(moves.stock_valuation_layer_ids.mapped('quantity')))

                    if bom_line.child_bom_id:
                        order = plan_orders.filtered(lambda o: o.bom_id == bom_line.child_bom_id)
                    else:
                        order = self.env['mrp.production']

                    material['cost'] += [{
                        'value': value,
                        'order': {'id': order.id, 'display_name': order.display_name},
                        'quantity': quantity
                    }]

                data['plans'] += [{
                    'id': plan.id,
                    'display_name': plan.plan_id,
                    'date': plan.date_finished.strftime('%d - %b - %Y'),
                    'product_qty': sum(productions.filtered(lambda o: o.bom_id == bom).mapped('product_qty')),
                    'product_uom_id': {'id': productions[0].product_uom_id.id, 'display_name': productions[0].product_uom_id.display_name}
                }]

            for key in ['bom_uom', 'secondary_uom', 'primary_uom']:
                _assign_cost_status(data[key]['cost'])
            
            for material in data['materials']:
                _assign_cost_status(material['cost'])

            data['plans'].reverse()

            record.report_data = json.dumps(data, indent=4, default=str)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """SELECT 
            DISTINCT ON (mp.bom_id) bom_id, 
            mp.bom_id AS id, 
            mp.id AS last_production_id,
            mp.date_finished AS last_production_date,
            mp.product_id AS product_id,
            mp.product_uom_id AS uom_id,
            mp.company_id AS company_id,
            pt.secondary_uom_id AS secondary_uom_id
        FROM 
            mrp_production mp
        LEFT JOIN
            mrp_plan plan
            ON (plan.id = mp.mrp_plan_id)
        LEFT JOIN
            product_product pp
            ON (pp.id = mp.product_id)
        LEFT JOIN
            product_template pt
            ON (pt.id = pp.product_tmpl_id)
        WHERE 
            mp.state = 'done' AND 
            mp.bom_id IS NOT NULL AND
            plan.state = 'done'
        ORDER BY 
            mp.bom_id, mp.date_finished desc
        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))