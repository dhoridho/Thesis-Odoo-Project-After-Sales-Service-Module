import json
from odoo import models, fields, api, _
from odoo.tools import float_compare
from collections import defaultdict


def _find(lines, line_id):
    for line in lines:
        if line['id'] == line_id:
            return line
    return False


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    cost_data = fields.Text(readonly=True)

    def _compute_show_valuation(self):
        for order in self:
            moves = order.move_raw_ids | order.move_finished_ids
            order.show_valuation = any(m.state == 'done' for m in moves)

    @api.model
    def _default_analytic_tags(self, context=None, user_id=None, company_id=None, branch_id=None, product_id=None):
        if context is None:
            context = self.env.context
        elif context is False:
            context = dict()

        default = context.get('default_analytic_tag_ids', False)
        if default:
            return default

        # do not apply for False
        if user_id is None:
            user_id = context.get('default_user_id', self.env.user)
        if company_id is None:
            company_id = context.get('default_company_id', self.env.company)
        if branch_id is None:
            branch_id = context.get('default_branch_id', self.env.branch if len(self.env.branches) == 1 else self.env['res.branch'])

        if isinstance(user_id, int):
            user_id = self.env['res.users'].browse(user_id)
        if isinstance(company_id, int):
            company_id = self.env['res.company'].browse(company_id)
        if isinstance(branch_id, int):
            branch_id = self.env['res.branch'].browse(branch_id)

        priorities = self.env['analytic.priority'].search([], order='priority')
        analytic_tags = self.env['account.analytic.tag']  
        for priority in priorities:
            if priority.object_id == 'user' and user_id.analytic_tag_ids:
                analytic_tags = user_id.analytic_tag_ids
                break
            elif priority.object_id == 'branch' and branch_id.analytic_tag_ids:
                analytic_tags = branch_id.analytic_tag_ids
                break
            elif priority.object_id == 'product_category' and product_id and product_id.categ_id.analytic_tag_ids:
                analytic_tags = product_id.categ_id.analytic_tag_ids
                break
        return [(6, 0, analytic_tags.ids)]

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytical Group', domain="[('company_id', '=', company_id)]", default=_default_analytic_tags)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'mrp_production_id', string='Valuations', readonly=True)
    mca_production_ids = fields.One2many('mrp.cost.actualization.production', 'production_id', string='MCA Cost Lines')
    estimated_cost_ids = fields.One2many('mrp.estimated.cost', 'production_id', string='Estimated Cost', readonly=False)

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _get_estimated_cost(self):
        if self.state != 'draft' or not self.product_id or not self.product_uom_id or not self.bom_id:
            return
        cost_values = self.bom_id._get_estimated_cost(self.product_id, self.product_qty, self.product_uom_id, self, 'production_id')
        self.estimated_cost_ids = [(5,)] + cost_values

    @api.onchange('user_id', 'company_id', 'branch_id', 'product_id')
    def onchange_branch(self):
        super(MrpProduction, self).onchange_branch()
        self.analytic_tag_ids = self._default_analytic_tags(context=False, user_id=self.user_id, company_id=self.company_id, branch_id=self.branch_id, product_id=self.product_id)

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        res = super(MrpProduction, self)._get_move_finished_values(product_id, product_uom_qty, product_uom, operation_id, byproduct_id)
        finished = self.env['mrp.bom.finished'].browse(self.env.context.get('finished_id', False))
        if finished:
            res['allocated_cost'] = finished.allocated_cost
        elif byproduct_id:
            res['allocated_cost'] = self.env['mrp.bom.byproduct'].browse(byproduct_id).allocated_cost
        return res
    
    def _get_and_predict_cost(self):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        total_material_cost = 0.0
        consumed_bom_lines = defaultdict(lambda: 0.0)
        for material in self.move_raw_ids.filtered(lambda o: o.state == 'done'):
            material_svls = material.stock_valuation_layer_ids.filtered(lambda o: o.quantity < 0.0)
            material_cost = abs(sum(material_svls.mapped('value')))
            material_qty = abs(sum(material_svls.mapped('quantity')))
            if material._has_bom_line():
                consumed_bom_lines[material.origin_bom_line_id] += material_qty
            total_material_cost += material_cost
        
        for material in self.move_raw_ids.filtered(lambda o: o.state not in ('done', 'cancel')):
            if material._has_bom_line():
                bom_line = self.env['mrp.bom.line'].browse(material.origin_bom_line_id)
                bom_qty = self.product_uom_id._compute_quantity(self.product_qty, self.bom_id.product_uom_id)
                should_consume_qty = bom_line.product_uom_id._compute_quantity(bom_line.product_qty * (bom_qty / self.bom_id.product_qty), material.product_uom)
                if float_compare(material.product_uom_qty, should_consume_qty, precision_rounding=material.product_uom.rounding) >= 0:
                    product_qty = material.product_qty
                else:
                    product_qty = material.product_uom._compute_quantity(should_consume_qty, material.product_id.uom_id) - consumed_bom_lines[material.origin_bom_line_id]
            else:
                product_qty = material.product_qty
            
            product = material.product_id.with_company(material.company_id)
            if is_cost_per_warehouse:
                product = product.with_context(price_for_warehouse=material.location_id.get_warehouse().id)
            unit_cost = product.standard_price
            material_cost = unit_cost * product_qty

            total_material_cost += material_cost

        byproduct_costs = defaultdict(lambda: 0.0)
        for move in self.move_byproduct_ids:
            byproduct_cost = (total_material_cost * move.allocated_cost) / 100
            byproduct_costs[move.id] = byproduct_cost
        
        return total_material_cost, byproduct_costs

    def _evaluate_valuations(self, cascade=False):
        self.ensure_one()

        company = self.company_id
        total_material_cost, move_costs = self._get_and_predict_cost()

        total_byproduct_cost, byproduct_svl_vals_list = self.move_byproduct_ids.filtered(lambda o: o.state == 'done')._production_revaluate_cost(company, move_costs)

        for move in self.move_finished_only_ids:
            finished_cost = ((total_material_cost - total_byproduct_cost) * move.allocated_cost) / 100
            move_costs[move.id] = finished_cost

        total_finished_cost, finished_svl_vals_list = self.move_finished_only_ids.filtered(lambda o: o.state == 'done')._production_revaluate_cost(company, move_costs)

        svl_vals_list = byproduct_svl_vals_list + finished_svl_vals_list

        if not svl_vals_list:
            return

        stock_valuation_layer_ids = self.env['stock.valuation.layer'].create(svl_vals_list)

        account_move_vals_list = []
        for svl in stock_valuation_layer_ids:
            account_move_vals_list += [svl._production_prepare_account_move_vals()]

        if account_move_vals_list:
            self.env['stock.valuation.layer']._production_create_account_moves(account_move_vals_list)
        
    def _account_entry_move(self):
        self.ensure_one()
        for consumption in self.consumption_ids.filtered(lambda o: o.state == 'confirm'):
            consumption._account_entry_move()

    def action_view_account_moves(self):
        self.ensure_one()
        moves = self.stock_valuation_layer_ids.mapped('account_move_id') 
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_journal_line')
        if len(moves) == 1:
            action['view_mode'] = 'form'
            action['views'] = [[False, 'form']]
            action['res_id'] = moves[0].id
        else:
            action['domain'] = [('id', 'in', moves.ids)]
        
        action['target'] = 'current'
        return action
