from odoo import api,models,fields

class returnRentalOrder(models.TransientModel):
    _name = 'rental.order.return'
    
    picking_ids = fields.Many2many('stock.picking')
    rental_id = fields.Many2one('rental.order')
    picking_domain_ids = fields.Many2many('stock.picking','return_rental_id','return_id','picking_return_id',compute='_compute_picking_domain_ids')
    
    
    @api.depends('rental_id')
    def _compute_picking_domain_ids(self):
        if self.rental_id:
            self.picking_domain_ids = [(6,0,self.rental_id.picking_ids.filtered(
                lambda line:line.state == 'done' and
                not line.rental_return and
                line.picking_type_code == "outgoing").ids
            )]
        else:
            self.picking_domain_ids = []
    
    
    @api.onchange('rental_id')
    def _onchange_rental_id(self):
        if self.rental_id:
            self.picking_ids = [(
                6,0,self.rental_id.picking_ids.filtered(
                    lambda line:line.state == 'done' and
                    not line.rental_return and
                    line.picking_type_code == "outgoing").ids
            )]
    
    
    def submit(self):
        if self.picking_ids:
            for data in self.picking_ids:
                return_obj = self.env['stock.return.picking'].sudo().create({'picking_id':data.id})
                return_obj._onchange_picking_id()
                if data.move_line_ids:
                    data_line = []
                    for move_line in data.move_line_ids:
                        data_line.append((0, 0, {
                            'product_id': move_line.product_id.id,
                            'lot_id': move_line.lot_id and move_line.lot_id.id,
                            'uom_id': move_line.product_uom_id.id,
                            'qty': move_line.qty_done,
                        }))
                    return_obj.return_line_ids = data_line
                return_obj.create_returns()
                data.rental_return = True
            