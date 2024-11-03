from datetime import datetime, date, time, timedelta
from odoo import api , fields , models, _
from odoo.exceptions import UserError, ValidationError, Warning

class RentalOrderChecklistLine(models.Model):
    _name = 'rental.order.checklist.line'
    _description = "Rental Order Checklist Line"

    item_id = fields.Many2one('rental.order.checklist.item', string="Item")
    # checklist_id = fields.Many2one('rental.order.checklist', string="Checklist")
    is_available = fields.Boolean(string="Available", default=True)
    price = fields.Float(string='Missing Cost')
    order_id = fields.Many2one('rental.order', string="Rental Order")
    stock_picking_id = fields.Many2one('stock.picking', string="Stock Picking")
    is_outitem = fields.Boolean(string="Out Item", default=True)
    is_initem = fields.Boolean(string="In Item", default=False)
    picking_type_code = fields.Selection(related='stock_picking_id.picking_type_code')
    lot_id = fields.Many2one(
        comodel_name='stock.production.lot',
        string='Serial Number',
        domain="[('id', 'in', lot_ids)]"
    )
    lot_ids = fields.Many2many(
        comodel_name='stock.production.lot',
        compute='_compute_lot_ids',
        string='Allowed Serial Numbers',
        store=False
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        compute="_compute_product_id",
        store=True
    )
    reff_id = fields.Integer(string="Refference ID", default=0)

    @api.depends('lot_id')
    def _compute_product_id(self):
        for line in self:
            if line.lot_id:
                line.product_id = line.lot_id.product_id.id

    @api.depends('order_id.rental_line.lot_id')
    def _compute_lot_ids(self):
        for line in self:
            line.lot_ids = line.order_id.mapped('rental_line.lot_id')

    @api.onchange('item_id')
    def _onchange_item_id(self):
        if self.item_id:
            self.price = self.item_id.price
        else:
            self.price = False

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    checklist_line_rental = fields.One2many(comodel_name='rental.order.checklist.line', inverse_name='stock_picking_id', string='Checklist Line', copy=True)
    is_checking_button_clicked = fields.Boolean(string='is_checking_button_clicked', default=False)
    confirm_rental = fields.Boolean(string='rental confirmed', default=False)
    is_confirm = fields.Boolean(string="Confirm", default=False)
    damage_cost_initem = fields.Float(string="Damage Cost")
    rental_id = fields.Many2one('rental.order', string='Rental Order', store=True)
    hide_confirm_checklist = fields.Boolean('Hide Confirm Checklist', default=False, compute='_compute_check_length_checklist_items')
    damage_cost_line_ids = fields.One2many(
        comodel_name='rental.order.damage.cost.line',
        inverse_name='stock_picking_id',
        string="Damage Cost Line"
    )

    @api.depends('checklist_line_rental')
    def _compute_check_length_checklist_items(self):
        for picking in self:
            if picking.checklist_line_rental:
                picking.hide_confirm_checklist = False
            else:
                picking.hide_confirm_checklist = True
    
    def rental_pickings(self):
        return self.filtered(lambda p: p.rental_id)

    # def button_validate(self):
    #     res = super(StockPickingInherit, self).button_validate()
    #     context = dict(self.env.context) or {}
    #     rental_id = self.rental_id
    #     rental_id.write({
    #         'damage_order_cost': self.damage_cost_initem
    #     })
    #     if not self.is_confirm and rental_id:
    #         raise ValidationError("Can't validate DO.Please confirm checklist line first! ")

    #     if self.state == 'done' and '/IN/' in self.name:
    #         ro_obj = self.env['rental.order'].search([('id', '=', self.rental_id.id)])
    #         ro_obj.action_close_rental()

    #     return res

    def button_validate(self):
        res = super(StockPickingInherit, self).button_validate()
        rental_id = self.rental_id
        rental_id.write({
            'damage_order_cost': self.damage_cost_initem
        })
        # make sure this method only apply for rental pickings
        rental_pickings = self.rental_pickings()
        if not rental_pickings:
            return res

        for record in rental_pickings:
            rental_id = record.rental_id
            if record.confirm_rental == True:
                if record.transfer_id and record.is_transfer_in:
                    picking_id = self.env['stock.picking'].search(
                        [('transfer_id', '=', record.transfer_id.id), ('is_transfer_out', '=', True),
                        ('state', '=', 'done')])
                    if not picking_id:
                        raise Warning("You can only validate Operation IN if the Operation OUT is validated")
                if record.state == 'done' and record.transfer_id:
                    record.transfer_id.calculate_transfer_qty(record)
                    if record.is_transfer_out or record.is_transfer_in:
                        for move in record.move_ids_without_package:
                            analytic_tag_ids = move.analytic_account_group_ids.mapped('analytic_distribution_ids')
                            for analytic_distribution_id in analytic_tag_ids:
                                vals = {
                                    'name': move.product_id.name,
                                    'account_id': analytic_distribution_id.account_id.id,
                                    'tag_ids': [(6, 0, analytic_distribution_id.tag_id.ids)],
                                    'partner_id': move.picking_id.partner_id.id,
                                    'company_id': move.picking_id.company_id.id,
                                    'amount': sum(move.stock_valuation_layer_ids.mapped('value')),
                                    'unit_amount': move.quantity_done,
                                    'product_id': move.product_id.id,
                                    'product_uom_id': move.product_uom.id,
                                    'general_account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                                }
                                analytic_entry_id = self.env['account.analytic.line'].create(vals)
                if record.transfer_id and 'Return' in record.origin:
                    for line in record.move_line_ids_without_package:
                        transist_line = record.transfer_id.product_line_ids.filtered(
                            lambda r: r.product_id.id == line.product_id.id)
                        transist_line.write({'return_qty': line.qty_done})

                return_date = fields.Datetime.now() + timedelta(
                    days=int(self.env["ir.config_parameter"].sudo().get_param("return_policy_days")))
                record.write({"return_date_limit": return_date})

                if record.transfer_id and record.is_transfer_out:
                    picking_id = self.env['stock.picking'].search(
                        [('transfer_id', '=', record.transfer_id.id), ('is_transfer_in', '=', True)], limit=1)
                    for move in picking_id.move_ids_without_package:
                        move.is_transfer_out = True
                for move in record.move_ids_without_package:
                    for lot in move.lot_ids:
                        if lot.alert_date and lot.expiration_date:
                            lot.alert_date = lot.expiration_date - timedelta(days=lot.product_id.alert_time)
                ml_sequence = 1
                for line in record.move_line_ids_without_package:
                    line.move_line_sequence = ml_sequence
                    ml_sequence += 1
            # if record.is_confirm == False and rental_id and record.checklist_line_rental:
            #     raise Warning("Can't validate DO. Please confirm checklist line first")
        return res

    def _change_rental_lines(self, lot_id):
        for rec in self:
            data = []
            for line in rec.rental_id.checklist_line_ids.filtered(lambda line:line.lot_id.id == lot_id):
                data.append((0, 0, {
                    'lot_id': line.lot_id.id,
                    'item_id': line.item_id.id,
                    'is_outitem': line.is_outitem,
                    'is_initem': line.is_initem,
                    'price': line.price,
                    'reff_id': line.id
                }))
            rec.checklist_line_rental = data


    def action_confirm_rental(self):
        for rec in self:
            if not rec.checklist_line_rental:
                rec.is_confirm = True
            if any(not line.is_outitem and line.is_initem for line in rec.checklist_line_rental):
                raise ValidationError("IN ITEM can’t be true if OUT ITEM false")
            else:
                rec.is_confirm = True

    # def button_validate_modified(self):
    #     res = super(StockPickingInherit, self).button_validate()
    #     rental_id = self.rental_id
    #     for record in self:
    #         if record.confirm_rental == True:
    #             if record.transfer_id and record.is_transfer_in:
    #                 picking_id = self.env['stock.picking'].search(
    #                     [('transfer_id', '=', record.transfer_id.id), ('is_transfer_out', '=', True),
    #                     ('state', '=', 'done')])
    #                 if not picking_id:
    #                     raise Warning("You can only validate Operation IN if the Operation OUT is validated")
    #             if record.state == 'done' and record.transfer_id:
    #                 record.transfer_id.calculate_transfer_qty(record)
    #                 if record.is_transfer_out or record.is_transfer_in:
    #                     for move in record.move_ids_without_package:
    #                         analytic_tag_ids = move.analytic_account_group_ids.mapped('analytic_distribution_ids')
    #                         for analytic_distribution_id in analytic_tag_ids:
    #                             vals = {
    #                                 'name': move.product_id.name,
    #                                 'account_id': analytic_distribution_id.account_id.id,
    #                                 'tag_ids': [(6, 0, analytic_distribution_id.tag_id.ids)],
    #                                 'partner_id': move.picking_id.partner_id.id,
    #                                 'company_id': move.picking_id.company_id.id,
    #                                 'amount': sum(move.stock_valuation_layer_ids.mapped('value')),
    #                                 'unit_amount': move.quantity_done,
    #                                 'product_id': move.product_id.id,
    #                                 'product_uom_id': move.product_uom.id,
    #                                 'general_account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
    #                             }
    #                             analytic_entry_id = self.env['account.analytic.line'].create(vals)
    #             if record.transfer_id and 'Return' in record.origin:
    #                 for line in record.move_line_ids_without_package:
    #                     transist_line = record.transfer_id.product_line_ids.filtered(
    #                         lambda r: r.product_id.id == line.product_id.id)
    #                     transist_line.write({'return_qty': line.qty_done})

    #             return_date = fields.Datetime.now() + timedelta(
    #                 days=int(self.env["ir.config_parameter"].sudo().get_param("return_policy_days")))
    #             record.write({"return_date_limit": return_date})

    #             if record.transfer_id and record.is_transfer_out:
    #                 picking_id = self.env['stock.picking'].search(
    #                     [('transfer_id', '=', record.transfer_id.id), ('is_transfer_in', '=', True)], limit=1)
    #                 for move in picking_id.move_ids_without_package:
    #                     move.is_transfer_out = True
    #             for move in record.move_ids_without_package:
    #                 for lot in move.lot_ids:
    #                     if lot.alert_date and lot.expiration_date:
    #                         lot.alert_date = lot.expiration_date - timedelta(days=lot.product_id.alert_time)
    #             ml_sequence = 1
    #             for line in record.move_line_ids_without_package:
    #                 line.move_line_sequence = ml_sequence
    #                 ml_sequence += 1
    #         elif rental_id:
    #             raise Warning("Can't validate DO. Please confirm checklist line first")
    #     return res

    def action_verify_rental(self):
        for record in self:
            rental_data = record.env['rental.order'].search([('name', '=', record.origin)])
            rental_data.write({'state': 'close'})
    
    def action_checking_rental(self):
        if self.is_checking_button_clicked == False:
            self.is_checking_button_clicked = True
        else: self.is_checking_button_clicked = False
