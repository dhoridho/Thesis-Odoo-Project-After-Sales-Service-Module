from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    reserved_by_id = fields.Many2one('res.users', string='Reserved By')
    reserved_availability = fields.Float('Quantity Reserved')
    is_reserved = fields.Boolean('Reserved')
    picking_id = fields.Many2one('stock.picking', 'Transfer', index=True, states={
                                 'done': [('readonly', True)]}, check_company=True)
    origin_src_location = fields.Char('Origin Source Location')
    origin_dest_location = fields.Char('Origin Destination Location')
    picking_reference = fields.Char(
        string="Picking Reference", related='picking_id.name')
    is_transit = fields.Boolean('Transit')
    date_done = fields.Datetime(related="picking_id.date_done")
    return_reason = fields.Many2one("return.reason", string="Return Reason")
    action = fields.Selection([('refund', 'Refund'), ('repair', 'Repair'), (
        'replace', 'Replace'), ('return', "Return")], string='Action', default='refund')
    is_transfer_in = fields.Boolean(string="Transit In")
    is_transfer_out = fields.Boolean(string="Transit Out")
    quantity_done = fields.Float(store=True)
    volume = fields.Float('Volume', compute='compute_volume')
    movement_type = fields.Selection([('receipt', 'Receipt'), ('delivery', 'Delivery'), ('internal', 'Internal'), ('manufacturing_in', "Manufacturing In"), ('transit_in', "Transit In"),
                                      ('transit_out', 'Transit Out'), ('adjustment_in', 'Adjustment In'), ('adjustment_out', 'Adjustment Out'), ('scrap', 'Scrap')], string='Movement Type', compute='_compute_movement_type', store=True)
    cost = fields.Float('Cost', default=0, compute='_compute_cost')

    def _compute_cost(self):
        for record in self:
            record.cost = record.product_id.product_tmpl_id.list_price * record.product_uom_qty

    def compute_volume(self):
        for record in self:
            record.volume = record.product_id.volume * record.product_uom_qty

    def action_done(self):
        for rec in self:
            rec.write({'state': 'done'})

    @api.depends('picking_type_id', 'location_id', 'location_dest_id', 'state')
    def _compute_movement_type(self):
        for record in self:
            transist_location = self.env.ref(
                'equip3_inventory_masterdata.location_transit')
            parent_location = self.env.ref(
                'stock.stock_location_locations_virtual')
            inv_adj_location = self.env['stock.location'].search([('usage', '=', 'inventory'), ('company_id', '=', record.company_id.id), ('location_id', '=', parent_location.id),
                                                                  ('name', 'ilike', 'Inventory adjustment')], limit=1)
            scrap_location = self.env['stock.location'].search([('usage', '=', 'inventory'), ('company_id', '=', record.company_id.id), ('location_id', '=', parent_location.id),
                                                                ('name', 'ilike', 'Scrap')], limit=1)
            if record.picking_type_id.code == 'incoming':
                record.movement_type = 'receipt'
            elif record.picking_type_id.code == 'outgoing':
                record.movement_type = 'delivery'
            elif record.picking_type_id.code == 'mrp_operation':
                record.movement_type = 'manufacturing_in'
            elif record.picking_type_id.code == 'internal':
                record.movement_type = 'internal'
            elif record.location_id.id == transist_location.id:
                record.movement_type = 'transit_in'
            elif record.location_dest_id.id == transist_location.id:
                record.movement_type = 'transit_out'
            elif record.location_id.id == inv_adj_location.id:
                record.movement_type = 'adjustment_in'
            elif record.location_dest_id.id == inv_adj_location.id:
                record.movement_type = 'adjustment_out'
            elif record.location_id.id == scrap_location.id:
                record.movement_type = 'scrap'
