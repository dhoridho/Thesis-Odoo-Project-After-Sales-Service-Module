from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TransferBackConsignment(models.TransientModel):
    _name = 'transfer.back.consignment'
    _description = 'Transfer Back Consignment Wizard'
    
    transfer_line = fields.One2many(comodel_name='transfer.back.consignment.line', inverse_name='transfer_back_id', string='Transfer Line')
    
    @api.model
    def default_get(self, default_fields):
        res = super(TransferBackConsignment, self).default_get(default_fields)
        
        context = self._context or {}
        active_model = context.get('active_model')
        
        if active_model == 'consignment.agreement':
            consignment_id = self.env['consignment.agreement'].browse(context.get('active_id'))
            if consignment_id and consignment_id.line_ids:
                lines = [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'warehouse_destination_id': line.destination_warehouse_id.id,
                        'available_qty': line.available_quantity,
                        'transfer_qty': 0
                    })
                    for line in consignment_id.line_ids if line.available_quantity > 0
                ]
                if lines:
                    res['transfer_line'] = lines
        
        return res
    
    def _create_do(self):
        StockPicking = self.env['stock.picking']
        context = self._context or {}
        consignment_id = self.env['consignment.agreement'].browse(context.get('active_id'))
        
        lines = []
        for line in self.transfer_line:
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'initial_demand': line.transfer_qty,
                'product_uom_qty': line.transfer_qty,
                'product_uom': line.product_id.uom_id.id,
                'name': line.product_id.name,
            }))
        print('➡ lines:', lines)
            
        customerloc = self.env['stock.warehouse']._get_partner_locations()[0]
            
        picking_vals = {
            'consignment_id': consignment_id.id,
            'branch_id': consignment_id.branch_id.id,
            'company_id': consignment_id.company_id.id,
            'location_id': consignment_id.destination_warehouse_id.lot_stock_id.id,
            'location_dest_id': customerloc.id,
            'picking_type_id': consignment_id.destination_warehouse_id.out_type_id.id,
            'origin' : consignment_id.name,
            'move_ids_without_package': lines
        }
        
        picking = StockPicking.create(picking_vals)
        if picking:
            consignment_id.picking_ids = [(4, picking.id)]
        
    
    def process(self):
        self._create_do()
        


class TransferBackConsignmentLine(models.TransientModel):
    _name = 'transfer.back.consignment.line'
    _description = 'Transfer Back Consignment Line'
    
    transfer_back_id = fields.Many2one(comodel_name='transfer.back.consignment', string='Consignment', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    warehouse_destination_id = fields.Many2one(comodel_name='stock.warehouse', string='Destination')
    available_qty = fields.Float(string='Available Quantity', readonly=True)
    transfer_qty = fields.Float(string='Transfer Quantity')
    