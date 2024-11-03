from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    stock_allocation_move_ids = fields.One2many('stock.allocation.move', 'picking_id', string='Allocation Moves')

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        self.check_allocation()
        self.subtract_allocation()
        return res
    
    # @api.model
    # def create(self, vals):
    #     picking = super(StockPicking, self).create(vals)
    #     picking.check_allocation()
    #     picking.subtract_allocation()
    #     return picking

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        self.return_allocation()
        return res

    def return_allocation(self):
        for picking in self:
            for allocation_move in picking.stock_allocation_move_ids:
                allocation_move.copy({
                    'qty': - allocation_move.qty,
                })
    
    def subtract_allocation(self):
        AllocationMove = self.env['stock.allocation.move']
        for picking in self:
            if picking.sale_channel_id and picking.sale_channel_id.allocate_on == 'picking' and picking.picking_type_id.id == picking.sale_channel_id.picking_type_id.id:
                warehouse = picking.location_id.get_warehouse()
                if not warehouse:
                    continue
                for move in picking.move_lines:
                    if move.product_uom_qty:
                        values = {
                            'date': move.date,
                            'product_id': move.product_id.id,
                            'warehouse_id': warehouse.id,
                            'location_id': self.location_id.id,
                            'sale_channel_id': self.sale_channel_id.id,
                            'move_id': move.id,
                            'picking_id': picking.id,
                            'qty': - move.product_uom_qty,
                        }
                        AllocationMove.create(values)

    def check_allocation(self):
        BalanceLine = self.env['stock.allocation.balance.line']
        # Check Allocation Balance
        for picking in self:
            if picking.sale_channel_id and picking.sale_channel_id.allocate_on == 'picking' and picking.sale_channel_id.check_allocation:
                warehouse = picking.location_id.get_warehouse()
                if not warehouse:
                    continue
                for move in picking.move_lines:
                    product = move.product_id
                    # Add Newest Moves
                    query = '''
                        SELECT 
                            COALESCE(sum(qty), 0) as qty
                        FROM stock_allocation_move 
                        WHERE warehouse_id = %s
                            AND product_id = %s
                            AND sale_channel_id = %s;
                    ''' % (warehouse.id,
                        product.id,
                        picking.sale_channel_id.id,
                    )
                    self.env.cr.execute(query)
                    balance_from_move_data = self.env.cr.dictfetchall()
                    total_balance = 0
                    if balance_from_move_data:
                        total_balance = balance_from_move_data[0]['qty']
                    # Check Order Qty
                    if move.product_uom_qty > total_balance:
                        raise UserError('Stock Allocation for Product %s on Sales Channel %s is less than order qty. Remaining allocation = %s' % (product.name, picking.sale_channel_id.name, total_balance))
