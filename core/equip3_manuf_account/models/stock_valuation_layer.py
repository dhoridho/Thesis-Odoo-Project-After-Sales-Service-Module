import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model
    def create(self, vals):
        if not vals.get('sequence_type', False):
            vals['sequence_type'] = 100 if vals.get('type', False) == 'finished' else 0
        return super(StockValuationLayer, self).create(vals)

    def write(self, vals):
        if 'type' in vals:
            vals['sequence_type'] = 100 if vals['type'] == 'finished' else 0
        return super(StockValuationLayer, self).write(vals)
    
    mrp_plan_id = fields.Many2one('mrp.plan', 'Production Plan', readonly=True, copy=False)
    mrp_production_id = fields.Many2one('mrp.production', 'Production Order', readonly=True, copy=False)
    mrp_workorder_id = fields.Many2one('mrp.workorder', 'Production Work Order', readonly=True, copy=False)
    mrp_consumption_id = fields.Many2one('mrp.consumption', 'Production Record', readonly=True, copy=False)

    mca_production_ids = fields.Many2many('mrp.cost.actualization.production', string='Production Cost Actualizations')
    type = fields.Selection(selection=[
        ('component', 'Material'),
        ('byproduct', 'By-Product'),
        ('finished', 'Finished Goods'),
        ('mca_material', 'Actualization - Material'),
        ('mca_labor', 'Actualization - Labor'),
        ('mca_overhead', 'Actualization - Overhead'),
        ('correction', 'Correction')
    ], string='Type', copy=False, default=False, readonly=True)
    
    sequence_type = fields.Integer(default=0)
    mca_last_unit_cost = fields.Monetary('Production Last Actualization Unit Value', readonly=True)
    mca_id = fields.Many2one('mrp.cost.actualization', string='Production Actualization', readonly=True)
    mca_operation_ids = fields.Many2many('mrp.routing.workcenter', 'svl_mca_operation_rel', 'svl_id', 'operation_id', string='Production Actualization Operations')
    mca_labor_ids = fields.Many2many('res.users', 'svl_mca_labor_rel', 'svl_id', 'user_id', string='Production Actualization Labors')

    def _production_prepare_account_move_vals(self):
        self.ensure_one()
        journal_id, debit_account_id, credit_account_id = self._get_stock_accounts()

        ref = _('Material Cost Changed')
        if self.mca_id:
            ref = self.mca_id.display_name

        return {
            'journal_id': journal_id,
            'company_id': self.company_id.id,
            'ref': ref,
            'stock_valuation_layer_ids': [(6, None, [self.id])],
            'date': fields.Date.today(),
            'move_type': 'entry',
            'name': '/',
            'state': 'draft',
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
                'product_id': self.product_id.id,
                'currency_id': self.company_id.currency_id.id,
            })],
        }

    @api.model
    def _production_create_account_moves(self, vals_list):
        """ overridden on equip3_manuf_inventory to replace with query 
        since `_query_create` is a method from equip3_inventory_operation
        """
        account_moves = self.env['account.move'].sudo().create(vals_list)
        if account_moves:
            account_moves._post()
