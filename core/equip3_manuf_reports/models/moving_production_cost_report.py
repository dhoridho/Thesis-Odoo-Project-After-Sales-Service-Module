import json
from odoo import models, fields, api, tools, _
from dateutil.relativedelta import relativedelta
from collections import defaultdict


class MovingProductionCostReport(models.Model):
    _name = 'moving.production.cost.report'
    _description = 'Moving Production Cost Report'
    _auto = False
    _rec_name = 'bom_id'

    bom_id = fields.Many2one('mrp.bom', string='Bill of Material')
    product_id = fields.Many2one('product.product', string='Product')
    last_production_date = fields.Date(string='Last Production Date')
    last_production_id = fields.Many2one('mrp.production', string='Last Production Order')
    production_ids = fields.Many2many('mrp.production', string='Production Orders', compute='_compute_productions')
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
                ('bom_id', '=', record.bom_id.id), ('state', '=', 'done'), 
                ('date_finished', '>=', record.date_from), 
                ('date_finished', '<=', record.date_to)
            ])
            record.production_ids = [(6, 0, production_ids.ids)]

    @api.depends_context('date_from', 'date_to')
    def _compute_date(self):
        today = fields.Date.today()
        self.date_from = self.env.context.get('date_from', today - relativedelta(days=30))
        self.date_to = self.env.context.get('date_to', today)

    @api.model
    def get_bom_line_data(self, bom, level=1):
        data = []
        for bom_line in bom.bom_line_ids:
            data += [{
                'id': bom_line.id,
                'level': level,
                'product': bom_line.product_id.display_name,
                'quantity': '%s %s' % (bom_line.product_qty, bom_line.product_uom_id.display_name),
                'cost': []
            }]
        return data

    @api.depends('bom_id', 'production_ids')
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

        def get_moves(orders):
            group = defaultdict(lambda: self.env['stock.move'])
            for order in orders:
                for move in order.move_raw_ids:
                    product = move.product_id
                    bom_line = move.bom_line_id
                    group[(product, bom_line)] |= move
            return group

        for record in self:
            bom = record.bom_id or self.env['mrp.bom']
            bom_product = bom.product_tmpl_id

            secondary_uom = bom_product.secondary_uom_id
            primary_uom = bom_product.uom_id
            sorted_production_ids = record.production_ids.sorted(key=lambda o: o.date_finished)

            group = get_moves(sorted_production_ids)

            data = {
                'productions': [],
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
                'bom_lines': self.get_bom_line_data(bom),
                'materials': [{
                    'product_id': {'id': product.id, 'display_name': product.display_name},
                    'bom_line_id': {'id': bom_line.id, 'display_name': bom_line.display_name},
                    'uom_id': {'id': product.uom_id.id, 'display_name': product.uom_id.display_name},
                    'product_qty': sum(move.product_qty for move in moves),
                    'moves': moves,
                    'cost': []
                } for (product, bom_line), moves in group.items()]
            }

            for production in sorted_production_ids:
                production_uom = production.product_uom_id
                value = abs(sum(production.move_finished_ids.filtered(lambda m: not m.byproduct_id).stock_valuation_layer_ids.mapped('value')))
                data['bom_uom']['cost'] += [{'value': value}]
                data['secondary_uom']['cost'] += [{'value': production_uom._compute_price(value / production.product_qty, secondary_uom)}]
                data['primary_uom']['cost'] += [{'value': production_uom._compute_price(value / production.product_qty, primary_uom)}]
                
                for material in data['materials']:
                    moves = material['moves'].filtered(lambda o: o.raw_material_production_id == production)
                    value = abs(sum(moves.stock_valuation_layer_ids.mapped('value')))
                    quantity = abs(sum(moves.stock_valuation_layer_ids.mapped('quantity')))

                    material['cost'] += [{
                        'value': value,
                        'quantity': quantity
                    }]

                data['productions'] += [{
                    'id': production.id,
                    'display_name': production.name,
                    'date': production.date_finished.strftime('%d - %b - %Y'),
                    'product_qty': production.product_qty,
                    'product_uom_id': {'id': production.product_uom_id.id, 'display_name': production.product_uom_id.display_name}
                }]

            for key in ['bom_uom', 'secondary_uom', 'primary_uom']:
                _assign_cost_status(data[key]['cost'])
            
            for material in data['materials']:
                _assign_cost_status(material['cost'])

            data['productions'].reverse()

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
            product_product pp
            ON (pp.id = mp.product_id)
        LEFT JOIN
            product_template pt
            ON (pt.id = pp.product_tmpl_id)
        WHERE 
            mp.state = 'done' AND mp.bom_id IS NOT NULL 
        ORDER BY 
            mp.bom_id, mp.date_finished desc
        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))