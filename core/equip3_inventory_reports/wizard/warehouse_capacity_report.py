
from odoo import tools
from odoo import fields, models, api
import base64
from io import BytesIO
import xlwt
from io import BytesIO
from xlsxwriter.workbook import Workbook

class WarehouseCapacityReport(models.TransientModel):
    _name = "warehouse.capacity.report"
    _description = 'Warehouse Capacity Report'

    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouses")
    location_ids = fields.Many2many('stock.location', string="Locations")
    filter_location_ids = fields.Many2many('stock.location', compute='_get_stock_locations', store=False)
    hide_location = fields.Boolean(default=False)


    @api.onchange('warehouse_ids')
    def update_locations_ids(self):
        if self.warehouse_ids:
            self.hide_location = True
        else:
            self.hide_location = False
        warehouse_list = []
        for ware in self.warehouse_ids:
            warehouse_list.append(ware.view_location_id.id)
        # print('warehouse_list', warehouse_list)
        for loc in self.location_ids:
            if loc.warehouse_id.view_location_id.id not in warehouse_list:
                self.write({'location_ids': [(3, loc.id)]})



    def warehouse_excel_report(self):
        file_name = 'Warehouse Capacity Report.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        format0 = xlwt.easyxf('font:height 500,bold True;pattern: pattern solid, fore_colour white;align: horiz center')
        format1 = xlwt.easyxf('font:height 200,bold True; align: horiz center')
        format2 = xlwt.easyxf('font:height 200,bold True; align: horiz left')
        format3 = xlwt.easyxf('font:height 200; align: horiz left')
        format4 = xlwt.easyxf('font:height 350,bold True;pattern: pattern solid, fore_colour white;align: horiz center')
        format5 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour white;align: horiz center')
        for record in self:
            warehouse_ids = record.warehouse_ids
            if not warehouse_ids:
                warehouse_ids = self.env['stock.warehouse'].search([])
            for warehouse in warehouse_ids:
                sheet = workbook.add_sheet('Warehouse : %s' % (warehouse.name))
                sheet.col(0).width = int(25*390)
                sheet.col(1).width = int(25*270)
                sheet.col(2).width = int(25*270)
                sheet.col(3).width = int(25*270)
                sheet.col(4).width = int(25*270)
                sheet.col(5).width = int(25*270)
                sheet.col(6).width = int(25*270)
                sheet.col(7).width = int(25*270)
                sheet.write_merge(0, 2, 0, 7, 'Warehouse Capacity Report', format0)
                sheet.write(8, 0, "Warehouse:", format2)
                warehouse_name = warehouse.name
                sheet.write(8, 1, warehouse_name, format3)
                sheet.write(10, 0, "Location", format2)
                sheet.write(10, 1, "Product", format2)
                sheet.write(10, 2, "On hand quantity", format2)
                sheet.write(10, 3, "Available quantity", format2)
                sheet.write(10, 4, "Unit of Measure", format2)
                sheet.write(10, 5, "Weight", format2)
                sheet.write(10, 6, "Total weight", format2)
                sheet.write(10, 7, "Unit weight", format2)
                if record.location_ids:
                    location = record.location_ids.filtered(lambda r: r.warehouse_id.id == warehouse.id)
                else:
                    location = self.env['stock.location'].search([('warehouse_id', '=', warehouse.id)])

                quant_ids = self.env['stock.quant'].search([('location_id', 'in', location.ids)])
                row = 11
                counter = 1
                product_line_data = []
                temp_list = []
                line_list_vals = []
                for line in quant_ids:
                    if {'product_id': line.product_id.id, 'location_id': line.location_id.id} in temp_list:
                        filter_list = list(filter(lambda r: r.get('product_id').id == line.product_id.id and r.get('location_id').id == line.location_id.id,  line_list_vals))
                        if filter_list:
                            filter_list[0]['available_quantity'].append(line.available_quantity)
                            filter_list[0]['quantity'].append(line.quantity)
                            filter_list[0]['weight'].append(line.weight)
                    else:
                        temp_list.append({'product_id': line.product_id.id, 'location_id': line.location_id.id})
                        line_list_vals.append({
                                'product_id' : line.product_id,
                                'location_id': line.location_id,
                                'weight': [line.weight],
                                'unit_weight': line.product_id.weight_uom_name,
                                'lot_id': line.lot_id.id,
                                'package_id': line.package_id.id,
                                'owner_id': line.owner_id.id,
                                'available_quantity' : [line.available_quantity],
                                'quantity' : [line.quantity],
                                'product_uom_id' : line.product_uom_id,
                            })
                for final_line in line_list_vals:
                    final_line['available_quantity'] = sum(final_line['available_quantity'])
                    final_line['quantity'] = sum(final_line['quantity'])
                    final_line['weight'] = sum(final_line['weight'])
                    final_line['total_weight'] = final_line['quantity'] * final_line['weight']
                    product_line_data.append(final_line)
                for product_line in product_line_data:
                    sheet.write(row, 0, product_line.get('location_id').display_name, format3)
                    sheet.write(row, 1, product_line.get('product_id').display_name, format3)
                    sheet.write(row, 2, product_line.get('quantity'), format3)
                    sheet.write(row, 3, product_line.get('available_quantity'), format3)
                    sheet.write(row, 4, product_line.get('product_uom_id').name, format3)
                    sheet.write(row, 5, product_line.get('weight'), format3)
                    sheet.write(row, 6, product_line.get("total_weight"), format3)
                    sheet.write(row, 7, product_line.get('unit_weight'), format3)
                    row += 1
                    counter += 1
            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['warehouse.capacity.excel.report'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                 'type' : 'ir.actions.act_url',
                 'url': '/web/binary/download_document?model=warehouse.capacity.excel.report&field=excel_file&id=%s&filename=%s'%(export_id.id, export_id.file_name),
                 'target': 'self',
            }


    @api.depends('warehouse_ids')
    def _get_stock_locations(self):
        for record in self:
            location_ids = []
            for warehouse in record.warehouse_ids:
                location_obj = self.env['stock.location']
                store_location_id = warehouse.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')], order='id')
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
            child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
            final_location = child_location_ids + location_ids
            record.filter_location_ids = [(6, 0, final_location)]
