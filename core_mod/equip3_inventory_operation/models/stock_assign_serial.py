# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import datetime
import base64
from xlrd import open_workbook


class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    def _default_next_serial_count(self):
        move = self.env['stock.move'].browse(
            self.env.context.get('default_move_id'))
        if move.exists():
            filtered_move_lines = move.move_line_ids.filtered(
                lambda l: not l.lot_name and not l.lot_id)
            return len(filtered_move_lines)

    picking_type_code = fields.Selection(
        related='move_id.picking_id.picking_type_code')
    serial_no = fields.Selection(related='product_id.tracking')
    export_file = fields.Binary("Upload File")
    export_name = fields.Char('Export Name', size=64)
    next_serial_number = fields.Char(
        'First SN', compute='_compute_next_serial', store=True, required=False)
    next_serial_count = fields.Integer('Number of SN',
                                       default=_default_next_serial_count, required=False)
    is_serial_number = fields.Boolean(
        string="Serial Number", related="product_id.is_sn_autogenerate")

    def generate_serial_numbers(self):
        self.ensure_one()

        if self.export_name:
            import_name_extension = self.export_name.split('.')[1]
            if import_name_extension not in ['xls', 'xlsx']:
                raise ValidationError('File format must be in xlsx or xls.')
        if self.export_file:
            workbook = open_workbook(
                file_contents=base64.decodestring(self.export_file))
            for sheet in workbook.sheets():
                line_list = []
                for count in range(1, sheet.nrows):
                    line_vals = {}
                    line = sheet.row_values(count)
                    categories_id = self.product_id.categ_id
                    if self.is_serial_number and self.product_id.tracking == 'serial':
                        current_name = ''
                        if self.product_id.is_use_product_code == True:
                            if self.product_id.sn_prefix:
                                current_name = self.product_id.default_code + self.product_id.sn_prefix
                            else:
                                current_name = self.product_id.default_code
                        else:
                            current_name = self.product_id.sn_prefix
                        if current_name and not line[0].startswith(current_name):
                            raise ValidationError(
                                _("The Lot/Serial Number that you imported must match prefix of the product Serial Number Master Data."))
                    line_vals['lot_name'] = line[0]
                    if line[1] != '':
                        package_id = self.env['stock.quant.package'].search(
                            [('name', 'ilike', line[1])], limit=1)
                        if not package_id:
                            package_id = self.env['stock.quant.package'].create(
                                {'name': line[1]})
                        line_vals['result_package_id'] = package_id and package_id.id or False
                    is_float = False
                    try:
                        is_float = float(line[2])
                    except ValueError:
                        pass
                    if not is_float:
                        raise ValidationError(
                            _("Done Value Must be in digits!"))
                    line_vals['qty_done'] = line[2]
                    line_vals['product_id'] = self.product_id.id
                    line_vals['product_uom_id'] = self.move_id.product_uom.id
                    line_vals['location_id'] = self.move_id.location_id.id
                    line_vals['location_dest_id'] = self.move_id.location_dest_id.id
                    if self.move_id.product_id.use_expiration_date:
                        line_vals['expiration_date'] = fields.Datetime.today(
                        ) + datetime.timedelta(days=self.move_id.product_id.expiration_time)
                    line_list.append((0, 0, line_vals))
            self.move_id.picking_id.write(
                {'move_line_nosuggest_ids': line_list})
            self.export_file = False
        else:
            return super(StockAssignSerialNumbers, self).generate_serial_numbers()

        return True

    @api.depends('product_id', 'product_id.default_code', 'product_id.sn_prefix',
                 'product_id.is_sn_autogenerate', 'product_id.is_use_product_code')
    def _compute_next_serial(self):
        for record in self:
            categories_id = record.product_id.categ_id
            next_serial = ''
            if record.product_id.is_sn_autogenerate == True:
                if record.product_id.is_use_product_code == True:
                    if record.product_id.sn_prefix:
                        current_name = record.product_id.default_code + \
                            record.product_id.sn_prefix + record.product_id.current_sequence
                        record.next_serial_number = current_name
                    else:
                        current_name = record.product_id.default_code + record.product_id.current_sequence
                        record.next_serial_number = current_name
                else:
                    current_name = record.product_id.sn_prefix + record.product_id.current_sequence
                    record.next_serial_number = current_name
