from odoo import _, api, fields, models
import json
from odoo.exceptions import ValidationError, Warning


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    sale_consignment_id = fields.Many2one(
        'sale.consignment.agreement', string='Consignment Agreement')
    is_transfer_back_consignment = fields.Boolean("Is Transfer Back")

    @api.model
    def create(self, vals):
        context = self._context or {}
        if context.get('active_model') == 'sale.consignment.agreement':
            sale_consignment_id = self.env['sale.consignment.agreement'].browse(
                context.get('active_id'))
            if sale_consignment_id.state in ('progress', 'done'):
                pass
            else:
                sale_consignment_id.write({'state': 'progress'})
            if sale_consignment_id and vals.get('is_transfer_back_consignment'):
                sale_consignment_id.write({'state': 'to_close'})
        return super(InternalTransfer, self).create(vals)

    @api.onchange('destination_location_id')
    def _compute_destination_loc(self):
        res = super()._compute_destination_loc()
        for record in self:
            if len(record.product_line_ids) != 0 and not record.destination_location_id:
                record.is_destination_loc = True
            else:
                record.is_destination_loc = False
        return res
    
    @api.onchange('source_location_id')
    def _compute_source_loc(self):
        if self.sale_consignment_id:
            self.is_source_loc = False
            for record in self.product_line_ids:
                record.source_location_id = self.source_location_id
        else:
            res = super(InternalTransfer, self)._compute_source_loc()

    @api.onchange('source_warehouse_id', 'destination_warehouse_id', 'is_single_source_location', 'is_single_destination_location')
    def _onchange_warehouse_id_for_location(self):
        for record in self:
            if record.sale_consignment_id and not record.is_transfer_back_consignment:
                if record.source_warehouse_id:
                    source_location_id = self.env['stock.location'].search(
                        [('warehouse_id', '=', record.source_warehouse_id.id), ('usage', '=', 'internal')], limit=1, order="id")
                    record.source_location_id = source_location_id
                    record.analytic_account_group_ids = record.source_warehouse_id.branch_id.analytic_tag_ids
            elif record.sale_consignment_id and record.is_transfer_back_consignment:
                skip = False
                if record.destination_warehouse_id:
                    destination_location_id = self.env['stock.location'].search(
                        [('warehouse_id', '=', record.destination_warehouse_id.id), ('usage', '=', 'internal')], limit=1, order="id")
                    record.destination_location_id = destination_location_id.id
                    record.analytic_account_group_ids = record.source_warehouse_id.branch_id.analytic_tag_ids
                    if record.destination_warehouse_id.branch_id.id == record.branch_id.id:
                        record.upd_dest()
                        skip = True
                if not skip:
                    for line in record.product_line_ids:
                        line.destination_location_id = False
            else:
                return super(InternalTransfer, self)._onchange_warehouse_id_for_location()

    def action_confirm(self):
        res = super(InternalTransfer, self).action_confirm()
        context = self._context
        if context.get('active_model') == 'sale.consignment.agreement':
            pickings = self.env['stock.picking'].search(
                [('transfer_id', '=', self.id), ('state', '=', 'draft')])
            for picking in pickings:
                picking.sale_consignment_id = picking.transfer_id.sale_consignment_id
                branch_id = picking.transfer_id.source_location_id.warehouse_id.branch_id.id,
                for move in picking.move_ids_without_package:
                    move.product_consignment_id = move.product_id
                if picking.is_transfer_out:
                    branch_id = picking.branch_id.id
                    picking.action_confirm()
                    picking.action_assign()
                if picking.is_transfer_in:
                    picking.branch_id = branch_id
        return res

    @api.onchange('destination_warehouse_id', 'source_warehouse_id', 'branch_id')
    def onchange_destination_warehouse_id(self):
        if self._context.get('active_model') != 'sale.consignment.agreement':
            return super(InternalTransfer, self).onchange_destination_warehouse_id()

        for rec in self:
            warehouse = rec.destination_warehouse_id if rec.is_transfer_back_consignment else rec.source_warehouse_id
            location_type = 'destination' if rec.is_transfer_back_consignment else 'source'

            if rec.destination_warehouse_id == rec.source_warehouse_id:
                raise ValidationError(
                    f'Source Warehouse ({rec.source_warehouse_id.name}) Cannot be the same as Destination Warehouse ({rec.destination_warehouse_id.name})')

            branch_id = rec.branch_id.id
            if branch_id != warehouse.branch_id.id:
                setattr(rec, f'{location_type}_warehouse_id', False)
                setattr(rec, f'{location_type}_location_id', False)


class InternalTransferLine(models.Model):
    _inherit = 'internal.transfer.line'

    product_consignment_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    product_id_domain = fields.Char(
        string="Product Domain", compute='_compute_product_id_domain')
    current_qty_consignment = fields.Float(string="Current Quantity", compute='_compute_current_qty_consignment')

    @api.depends('product_consignment_id')
    def _compute_product_id_domain(self):
        product_tmpl_ids = self.env['sale.consignment.agreement'].search(
            [('id', '=', self.product_line.sale_consignment_id.id)], limit=1).consignment_line_ids.mapped('product_id')
        product_ids = self.env['product.product'].search(
            [('product_tmpl_id', 'in', product_tmpl_ids.ids)])

        existing_product_ids = self.product_line.product_line_ids.mapped(
            'product_id').ids

        new_product_ids = [
            product_id.id for product_id in product_ids if product_id.id not in existing_product_ids]

        domain = json.dumps(['|',('id', 'in', new_product_ids),('sale_ok', '=', True),('type','=','product'),('is_consignment_sales','=',True)])

        self.product_id_domain = domain

    @api.onchange('product_consignment_id')
    def onchange_product_consignment(self):
        if self.product_consignment_id:
            self.product_id = self.product_consignment_id
            
            for consignment_line in self.product_line.sale_consignment_id.consignment_line_ids:
                if consignment_line.product_id.id == self.product_consignment_id.product_tmpl_id.id:
                    self.current_qty_consignment = consignment_line.current_qty

    @api.onchange('qty')
    def onchange_qty(self):
        if self.product_consignment_id and self.product_line.is_transfer_back_consignment:
            consignment_lines = self.product_line.sale_consignment_id.consignment_line_ids.filtered(
                lambda line: self.env['product.product'].search(
                    [('product_tmpl_id', '=', line.product_id.id)], limit=1).id == self.product_consignment_id.id
            )
            if any(self.qty > line.current_qty for line in consignment_lines):
                raise ValidationError(
                    'Quantity cannot be greater than current quantity consignment agreement')


    @api.depends('product_line.sale_consignment_id')
    def _compute_current_qty_consignment(self):
        for rec in self:
            rec.current_qty_consignment = 0
            product_tmpl_id = rec.product_id.product_tmpl_id
            for consigment_line in rec.product_line.sale_consignment_id.consignment_line_ids:
                if product_tmpl_id.id == consigment_line.product_id.id:
                    rec.current_qty_consignment = consigment_line.current_qty
