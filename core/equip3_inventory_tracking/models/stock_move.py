
from datetime import timedelta
from time import time
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    exp_date = fields.Datetime(string="Expiration Date")
    qty_bundle = fields.Integer("Qty Bundle")
    id_bundle = fields.Integer("Product Bundle id")
    package_barcode = fields.Char(string="Packaging Barcode")
    
    @api.onchange('exp_date')
    def onchange_exp_date(self):
        for move in self:
            for move_line in move.move_line_nosuggest_ids:
                move_line.exp_date = move.exp_date

    @api.onchange('product_uom_qty')
    def _onchange_qty_bundle(self):
        if self.product_uom_qty and self.product_id.is_pack:
            self.qty_bundle = self.product_uom_qty

    @api.model_create_multi
    def create(self, values):
        res = super(StockMove, self).create(values)
        for move in res:
            if move.create_date and move.product_id.product_tmpl_id.use_expiration_date:
                move.exp_date = move.create_date + timedelta(days=move.product_id.expiration_time)
        return res

    @api.constrains("create_date")
    def _product_set_exp_date(self):
        for rec in self:
            if rec.product_id and rec.create_date:
                rec.exp_date = rec.create_date + timedelta(days=rec.product_id.expiration_time)

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        for rec in self:
            if rec.is_pack == True:
                rec.is_pack = True
            else:
                rec.is_pack = False

    @api.constrains('move_line_nosuggest_ids')
    def check_lot_serial_unique(self):
        for record in self:
            for move_line in record.move_line_nosuggest_ids:
                if move_line.lot_name:
                    domain = [('product_id', '!=', move_line.product_id.id), ('company_id', '=', move_line.company_id.id), '|', ('name', '=', move_line.lot_name), ('name', '=', (' '+move_line.lot_name))]
                    exist_lot = self.env['stock.production.lot'].search(domain, limit=1)
                    if exist_lot:
                        raise ValidationError(_('Existing Serial number (%s). Please choose a different sequence.') % move_line.lot_name)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model
    def create(self, values):
        move_id = values.get('move_id', False)
        if move_id:
            move = self.env['stock.move'].browse(move_id)
            lot = False
            if values.get('lot_id'):
                lot = self.env['stock.production.lot'].search([('id', '=', values['lot_id'])])
            if not values.get('exp_date', False) and not lot:
                values['exp_date'] = move.exp_date
            else:
                values['exp_date'] = values.get('exp_date', False)

        return super(StockMoveLine, self).create(values)
    
    exp_date = fields.Datetime(string='Expiration Time')

    def _assign_production_lot(self, lot):
        super()._assign_production_lot(lot)
        self.lot_id._update_date_values(self.exp_date)


    @api.onchange('lot_name', 'lot_id')
    def _onchange_serial_number(self):
        res = super(StockMoveLine, self)._onchange_serial_number()
        if self.lot_id:
            self.exp_date = self.lot_id.expiration_date
        return res