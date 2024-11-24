import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_is_zero
from collections import defaultdict
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model
    def _stock_move_type_selection(self):
        valued_types = self.env['stock.move']._get_valued_types()
        return [(valued_type, valued_type.replace('_', ' ').title()) for valued_type in valued_types]

    @api.depends('stock_move_id')
    def _compute_stock_move_type(self):
        valued_types = self.env['stock.move']._get_valued_types()
        for svl in self:
            stock_move_type = False
            svl_move = svl.stock_move_id
            if svl_move:
                for valued_type in valued_types:
                    if getattr(svl_move, '_is_%s' % valued_type)():
                        stock_move_type = valued_type
                        break
            svl.stock_move_type = stock_move_type
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', compute='_compute_picking')
    sale_id = fields.Many2one('sale.order', string='Sale Order', compute='_compute_sale')
    move_internal_type = fields.Selection(selection=[
        ('in', 'Internal In'),
        ('out', 'Internal Out')
    ], default=False, copy=False)

    product_cost_method = fields.Selection(related='categ_id.property_cost_method', readonly=True)
    standard_remaining_qty = fields.Float(digits=0, readonly=True)
    stock_move_type = fields.Selection(selection=_stock_move_type_selection, compute='_compute_stock_move_type')

    landed_partner_id = fields.Many2one('res.partner', string='Landed Cost Vendor')
    landed_service_product_id = fields.Many2one('product.product', string='Landed Cost Service Product')

    """ The reason this field still exists is that this field is still used in the project """
    source_ids = fields.Many2many('stock.valuation.layer.source', string='Valuation Source', readonly=True)

    @api.depends('stock_move_id', 'stock_move_id.picking_id')
    def _compute_picking(self):
        for record in self:
            picking_id = False
            if record.stock_move_id:
                picking_id = record.stock_move_id.picking_id.id
            record.picking_id = picking_id

    @api.depends('picking_id')
    def _compute_sale(self):
        for record in self:
            sale_id = False
            if record.picking_id:
                sale_id = record.picking_id.sale_id.id
            record.sale_id = sale_id

    def _change_standard_price_prepare_account_move_vals(self, new_price):
        res = super(StockValuationLayer, self)._change_standard_price_prepare_account_move_vals(new_price)
        if self.env.context.get('inventory_id', False):
            inventory = self.env['stock.inventory'].browse(self.env.context.get('inventory_id', False))
            branch = inventory.branch_id
        else:
            branch = self.env.branch
        return self.env['account.move']._query_complete_account_move_fields(res, branch)

    def _fifo_revaluate_prepare_account_move_vals(self):
        res = super(StockValuationLayer, self)._fifo_revaluate_prepare_account_move_vals()
        return self.env['account.move']._query_complete_account_move_fields(res, self.inventory_id.branch_id)

    def _get_stock_accounts(self):
        journal_id, debit_account_id, credit_account_id = super(StockValuationLayer, self)._get_stock_accounts()
        
        if self.stock_landed_cost_id:
            valuation_account_id = self.product_id.categ_id.property_stock_valuation_account_id.id
            expense_account_id = self.landed_service_product_id.categ_id.property_account_expense_categ_id.id

            if not valuation_account_id:
                raise UserError(_('Please set stock valuation account for product %s' % self.product_id.display_name))
            if not expense_account_id:
                raise UserError(_('Please set expense account for product %s' % self.landed_service_product_id.display_name))

            debit_account_id = valuation_account_id
            credit_account_id = expense_account_id
            if self.value < 0.0:
                debit_account_id, credit_account_id = credit_account_id, debit_account_id
                
        return journal_id, debit_account_id, credit_account_id

    def _prepare_account_move_vals(self):
        self.ensure_one()
        journal_id, debit_account_id, credit_account_id = self._get_stock_accounts()

        if self.stock_landed_cost_id:
            credit_product = self.landed_service_product_id
        else:
            credit_product = self.product_id

        move_vals = {
            'name': self.env['account.journal'].browse(journal_id).sequence_id.next_by_id(),
            'journal_id': journal_id,
            'company_id': self.company_id.id,
            'ref': self.description,
            'stock_valuation_layer_ids': [(6, None, [self.id])],
            'date': fields.Date.today(),
            'move_type': 'entry',
            'state': 'posted',
            'currency_id': self.company_id.currency_id.id,
            'line_ids': [(0, 0, {
                'name': self.description,
                'account_id': debit_account_id,
                'debit': abs(self.value),
                'credit': 0,
                'product_id': self.product_id.id,
                'currency_id': self.company_id.currency_id.id,
            }), (0, 0, {
                'name': self.description,
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(self.value),
                'product_id': credit_product.id,
                'currency_id': self.company_id.currency_id.id,
            })],
        }
        return self.env['account.move']._query_complete_account_move_fields(move_vals, self.env.branch)

    def _adjust_history(self, new_unit_cost, description, domain=None):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        svl_vals_list = []
        for svl in self:
            if svl.product_id.cost_method not in ('average', 'fifo'):
                continue

            domain_lines = [
                ('svl_id', '>', svl.id),
                ('product_id', '=', svl.product_id.id),
                ('quantity', '!=', 0.0)
            ]
            if domain:
                domain_lines = expression.AND([domain_lines, domain])

            lines_to_adjust = svl.line_ids | self.env['stock.valuation.layer.line'].search(domain_lines)

            group = defaultdict(lambda: self.env['stock.valuation.layer.line'])
            for svl_line in lines_to_adjust:
                currency = svl_line.company_id.currency_id
                diff_cost = new_unit_cost - svl_line.unit_cost
                if currency.is_zero(diff_cost):
                    continue
                
                svl_type = 'out' if svl_line.quantity < 0.0 else 'in'
                group[svl_line.product_id, svl_line.warehouse_id, svl_line.location_id, svl_type, diff_cost] |= svl_line

            svl_line_group = defaultdict(lambda: [])
            for (product, warehouse, location, svl_type, diff_cost), group_svl_lines in group.items():
                line_values = []
                for svl_line in group_svl_lines:

                    values = {
                        'quantity': 0,
                        'unit_cost': 0,
                        'value': svl_line.quantity * diff_cost,
                        'lot_id': svl_line.lot_id.id,
                        'description': description
                    }

                    if svl_type == 'in':
                        svl_line.remaining_value += diff_cost * svl_line.remaining_qty
                    line_values += [values]

                svl_vals_list += [{
                    'company_id': svl_line.company_id.id,
                    'product_id': product.id,
                    'description': description,
                    'value': sum(o['value'] for o in line_values),
                    'quantity': 0,
                    'unit_cost': 0,
                    'warehouse_id': warehouse.id,
                    'location_id': location.id,
                    'stock_valuation_layer_id': svl.id,
                    'lot_ids': [(6, 0, [o['lot_id'] for o in line_values if o['lot_id']])],
                    'line_ids': [(0, 0, o) for o in line_values]
                }]

                svl_line_group[(warehouse.id, location.id)] += line_values

            for svl in lines_to_adjust.mapped('svl_id').filtered(lambda o: o.remaining_qty):
                svl.remaining_value = sum(svl.line_ids.mapped('remaining_value'))

        if not svl_vals_list:
            return self.browse()

        stock_valuation_layers = self.env['stock.valuation.layer'].create(svl_vals_list)

        groups = defaultdict(lambda: self.env['stock.valuation.layer'])
        for svl in stock_valuation_layers:
            groups[svl.product_id, svl.warehouse_id, svl.company_id] |= svl

        for (product, warehouse, company), svl_groups in groups.items():
            product_contexed = product.with_company(company)
            if is_cost_per_warehouse:
                product_contexed = product_contexed.with_context(price_for_warehouse=warehouse.id)

            if product.cost_method == 'fifo':
                domain = [
                    ('company_id', '=', company.id),
                    ('product_id', '=', product.id),
                    ('remaining_qty', '>', 0.0)
                ]
                if is_cost_per_warehouse:
                    domain += [('warehouse_id', '=', warehouse.id)]
                
                next_candidate = self.env['stock.valuation.layer.line'].sudo().search(domain, limit=1)
                if next_candidate:
                    product_contexed.with_context(disable_auto_svl=True).standard_price = next_candidate.remaining_value / next_candidate.remaining_qty

            elif product.cost_method == 'average':
                quantity_svl = product_contexed.quantity_svl
                if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                    value_svl = product_contexed.value_svl
                    product_contexed.with_context(disable_auto_svl=True).standard_price = value_svl / quantity_svl

        account_move_vals_list = []
        for svl in stock_valuation_layers:
            if svl.product_id.valuation != 'real_time':
                continue
            account_move_vals_list  += [svl._prepare_account_move_vals()]

        if account_move_vals_list:
            self.env['account.move']._query_create(account_move_vals_list)

        return stock_valuation_layers


class StockValuationLayerLine(models.Model):
    _inherit = 'stock.valuation.layer.line'

    svl_source_line_id = fields.Many2one('stock.valuation.layer.line', string='Valuation Line Source')
    svl_source_id = fields.Many2one('stock.valuation.layer', string='Valuation Source') # this field should be related `svl_source_line_id.svl_id`
    stock_move_source_id = fields.Many2one(related='svl_source_id.stock_move_id', string='Source Stock Move')
    picking_source_id = fields.Many2one(related='svl_source_id.picking_id', string='Source Receiving Notes')
    standard_remaining_qty = fields.Float(digits=0, readonly=True)
    sale_line_purchase_price = fields.Float(related='stock_move_id.sale_line_id.purchase_price')

    mark_id = fields.Integer()

    def _source(self):
        self.ensure_one()
        line = self
        while line.svl_source_line_id.exists():
            line = line.svl_source_line_id
        return line

    def _prepare_candidate_values(self, quantity=0.0):
        res = super(StockValuationLayerLine, self)._prepare_candidate_values(quantity=quantity)
        source = self._source()
        res.update({
            'svl_source_line_id': source.id,
            'svl_source_id': source.svl_id.id
        })
        return res


""" The reason this model still exists is that this model is still used in the project """
class StockValuationLayerSource(models.Model):
    _name = 'stock.valuation.layer.source'
    _description = 'Valuation Source'

    svl_id = fields.Many2one('stock.valuation.layer', string='Valuation', required=True, delegate=True, ondelete='cascade')
    taken_qty = fields.Float(digits=0, readonly=True, help='Quantity taken from this valuation.')
