# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import datetime, re
import base64
from xlrd import open_workbook


class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    picking_type_code = fields.Selection(related='move_id.picking_id.picking_type_code')

    tracking = fields.Selection(related='product_id.tracking')
    export_file = fields.Binary("Upload File")
    export_name = fields.Char('Export Name', size=64)
    is_serial_auto = fields.Boolean(related="product_id.is_sn_autogenerate")
    next_serial_count = fields.Integer(required=False)

    def generate_serial_numbers(self):
        self.ensure_one()

        if self.export_name:
            import_name_extension = self.export_name.split('.')[1]
            if import_name_extension not in ['xls', 'xlsx']:
                raise ValidationError('File format must be in xlsx or xls.')
        if self.export_file:
            workbook = open_workbook(file_contents=base64.decodestring(self.export_file))
            for sheet in workbook.sheets():
                line_list = []
                for count in range(1, sheet.nrows):
                    line_vals = {}
                    line = sheet.row_values(count)

                    if self.product_id._is_sn_auto():
                        sequence = self._get_next_lot_and_serial(join=False)
                        sequence[-2] = '(\\d+)'
                        lot_exp = ''.join([seq for seq in sequence if seq])

                        exp_match = re.search(lot_exp, line[0])
                        if not exp_match:
                            raise ValidationError(_("The Lot/Serial Number doesn't match with format from master data."))
                    
                    line_vals['lot_name'] = line[0]
                    if line[1] != '':
                        package_id = self.env['stock.quant.package'].search(
                            [('name', 'ilike', line[1])], limit=1)
                        if not package_id:
                            package_id = self.env['stock.quant.package'].create({'name': line[1]})
                        line_vals['result_package_id'] = package_id and package_id.id or False
                    
                    is_float = False
                    try:
                        is_float = float(line[2])
                    except ValueError:
                        pass
                    if not is_float:
                        raise ValidationError(_("Done Value Must be in digits!"))
                    
                    line_vals['qty_done'] = line[2]
                    line_vals['product_id'] = self.product_id.id
                    line_vals['product_uom_id'] = self.move_id.product_uom.id
                    line_vals['location_id'] = self.move_id.location_id.id
                    line_vals['location_dest_id'] = self.move_id.location_dest_id.id
                    if self.product_id.use_expiration_date:
                        line_vals['expiration_date'] = fields.Datetime.today() + datetime.timedelta(days=self.move_id.product_id.expiration_time)
                    line_list.append((0, 0, line_vals))
            
            self.move_id.picking_id.write({'move_line_nosuggest_ids': line_list})
            self.export_file = False
        
        return super(StockAssignSerialNumbers, self).generate_serial_numbers()
