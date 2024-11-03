from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    stock_allocation_move_ids = fields.One2many('stock.allocation.move', 'sale_id', string='Allocation Moves')

    # @api.model
    # def create(self, vals):
    #     order = super(SaleOrder, self).create(vals)
    #     order.check_allocation()
    #     order.subtract_allocation()
    #     return order
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.check_allocation()
        self.subtract_allocation()
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self.return_allocation()
        return res
    
    def return_allocation(self):
        for order in self:
            for allocation_move in order.stock_allocation_move_ids:
                allocation_move.copy({
                    'qty': - allocation_move.qty,
                })
    
    def subtract_allocation(self):
        AllocationMove = self.env['stock.allocation.move']
        # Check Allocation Balance
        for order in self:
            if order.sale_channel_id and order.sale_channel_id.allocate_on == 'sale':
                for line in order.order_line:
                    if line.product_uom_qty:
                        values = {
                            'date': order.date_order,
                            'product_id': line.product_id.id,
                            'warehouse_id': order.warehouse_id.id,
                            'location_id': order.warehouse_id.lot_stock_id.id,
                            'sale_channel_id': order.sale_channel_id.id,
                            'move_id': False,
                            'picking_id': False,
                            'sale_line_id': line.id,
                            'sale_id': order.id,
                            'qty': - line.product_uom_qty,
                        }
                        AllocationMove.create(values)

    def check_allocation(self):
        BalanceLine = self.env['stock.allocation.balance.line']
        # Check Allocation Balance
        for order in self:
            if order.sale_channel_id and order.sale_channel_id.allocate_on == 'sale' and order.sale_channel_id.check_allocation:
                for line in order.order_line:
                    product = line.product_id
                    # Add Newest Moves
                    query = '''
                        SELECT 
                            COALESCE(sum(qty), 0) as qty
                        FROM stock_allocation_move 
                        WHERE warehouse_id = %s
                            AND product_id = %s
                            AND sale_channel_id = %s;
                    ''' % (order.warehouse_id.id,
                        product.id,
                        order.sale_channel_id.id,
                    )
                    self.env.cr.execute(query)
                    balance_from_move_data = self.env.cr.dictfetchall()
                    total_balance = 0
                    if balance_from_move_data:
                        total_balance = balance_from_move_data[0]['qty']
                    # Check Order Qty
                    if line.product_uom_qty > total_balance:
                        raise UserError('Stock Allocation for Product %s on Sales Channel %s is less than order qty. Remaining allocation = %s' % (product.name, order.sale_channel_id.name, total_balance))
