# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import Warning
import logging
import tempfile
import binascii
import datetime

_logger = logging.getLogger(__name__)
import io
import re

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ImportClient(models.TransientModel):
    _name = "import.inventory.adjustment"
    _description = 'import inventory adjustment'

    inventory_name = fields.Char(string='Inventory Name')
    location = fields.Many2one('stock.location', string='Location')
    product_new = fields.Many2one('product.product',string='product')
    import_serial = fields.Boolean(string='Import serial/Lot number with expire date',default=True)
    import_location = fields.Boolean(string='Import Location on line',default=True)
    import_file = fields.Binary(string="Add File")
    product_by = fields.Selection([('name', 'Name'), ('code', 'Default Code'), ('barcode', 'Barcode')],
                                  string='Import Product By', default='name')
    file_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select File', default='csv')

    def import_inventory_adjustment_action(self):
        if self.file_option == 'csv':
            
            csv_data = base64.b64decode(self.import_file)
            data_file = io.StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            csv_reader = csv.DictReader(data_file, delimiter=',')
           
            product = self.env['product.product']
            stock_info = self.env['stock.inventory']
            package_info = self.env['stock.quant.package']
            location_info= self.env['stock.location']
            lot_number = self.env['stock.production.lot']

            for line in csv_reader:

                if self.product_by == 'name':
                    if line.get('Product Name'):
                        product_info = product.search([('name', '=', line.get('Product Name'))])
                        if not product_info:
                            product_info = product_info.create({
                                'name': line.get('Product Name'),
                            })


                if self.product_by == 'code':
                    if line.get('Product Code'):
                        product_info = product.search([('code', '=', line.get('Product Code'))])
                        if not product_info:
                            product_info = product_info.create({
                                'code': line.get('Product Code'),
                            })

                if self.product_by == 'barcode':
                    if line.get('Product Barcode'):
                        product_info = product.search([('barcode', '=', line.get('Product Barcode'))])
                        if not product_info:
                            product_info = product_info.create({
                                'barcode': line.get('Product Barcode'),
                            })


                if line.get('Location'):
                    location_info = location_info.search([('name', '=', line.get('Location'))])
                    if not location_info:
                        location_info = location_info.create({
                            'name': line.get('Location'),
                        })

              
                if line.get('Lot Serial Number'):
                    lot_number = lot_number.search([('name', '=', line.get('Lot Serial Number'))])
                    print("33333333333333",lot_number)
                    # if not lot_number:
                    #     lot_number = lot_number.create({
                    #         'name': line.get('Lot Serial Number'),
                    #         'product_id':line.get('Product Name')
                    #     })
                    #     print("ghghghhhhh____________",package_info)



                if line.get('Package'):
                    package_info = package_info.search([('name', '=', line.get('Package'))])
                    if not package_info:
                        package_info = package_info.create({
                            'name': line.get('Package'),
                        })

                        
                       
                if line.get('Date'):
                    date = datetime.datetime.strptime(line['Date'], '%m/%d/%Y')
                else:
                    date = datetime.datetime.now()


                inventory = self.env['stock.inventory'].create({
                    'name': self.inventory_name,
                    'location_ids': [(4, self.location.id)],
                   
                })
                inventory.action_start()
                if self.import_location:
                    info = self.env['stock.inventory.line'].create({
                        'product_id': product_info.id,
                        'inventory_id': inventory.id,
                        'location_id': inventory.location_ids[0].id,
                        'inventory_date': date,
                        'prod_lot_id':lot_number.id,
                        'package_id':package_info.id,
                        'theoretical_qty': line.get('Quantity'),
                    })

                if self.import_serial:
                    info_serial = self.env['stock.production.lot'].create({
                        'product_id': product_info.id,
                        'name':line.get('Lot Serial Number'),
                        'company_id':  self.env.company.id,
                       
                    })


        elif self.file_option == 'xls':
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.import_file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            keys = sheet.row_values(0)
            xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]
           

            partner = self.env['res.partner']
            product_name = self.env['product.product']
            product = self.env['product.template']
            currency = self.env['res.currency']

           

            for row in xls_reader:
                line = dict(zip(keys, row))

                if line.get('Product Name'):
                    product_info = product.search([('name', '=', line.get('Product Name'))])

                if line.get('Location'):
                    location_info = location_info.search([('name', '=', line.get('Location'))])
                    if not location_info:
                        location_info = location_info.create({
                            'name': line.get('Location'),
                        })

              
                if line.get('Lot Serial Number'):
                    lot_number = lot_number.search([('name', '=', line.get('Lot Serial Number'))])
                    # if not lot_number:
                    #     lot_number = lot_number.create({
                    #         'name': line.get('Lot Serial Number'),
                    #         'product_id':line.get('Product Name')
                    #     })
                    #     print("ghghghhhhh____________",package_info)



                if line.get('Package'):
                    package_info = package_info.search([('name', '=', line.get('Package'))])
                    if not package_info:
                        package_info = package_info.create({
                            'name': line.get('Package'),
                        })

                        
                       
                if line.get('Date'):
                    date = datetime.datetime.strptime(line['Date'], '%m/%d/%Y')
                else:
                    date = datetime.datetime.now()


                inventory = self.env['stock.inventory'].create({
                    'name': self.inventory_name,
                    'location_ids': [(4, self.location.id)],
                   
                })
                inventory.action_start()
                if self.import_location:
                    info = self.env['stock.inventory.line'].create({
                        'product_id': product_info.id,
                        'inventory_id': inventory.id,
                        'location_id': inventory.location_ids[0].id,
                        'inventory_date': date,
                        'prod_lot_id':lot_number.id,
                        'package_id':package_info.id,
                        'theoretical_qty': line.get('Quantity'),
                    })

                if self.import_serial:
                    info_serial = self.env['stock.production.lot'].create({
                        'product_id': product_info.id,
                        'name':line.get('Lot Serial Number'),
                        'company_id':  self.env.company.id,
                       
                    })
          

        else:
            raise Warning(_("Invalid file!"))


     