import csv
import base64
from io import StringIO
from odoo import api, fields, models, _ 
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import os


class PickingWizardImport(models.TransientModel):
    _name = 'picking.wizard.import'
    _description = 'Picking Wizard Import'

    file = fields.Binary(string='File')
    file_name = fields.Char(string='File Name')

    def import_csv_data(self):
        try:
            # Decode the base64-encoded CSV file
            csv_data = base64.b64decode(self.file)

            # Create a CSV reader object
            csv_reader = csv.DictReader(csv_data.decode('utf-8').splitlines())

            picking_dict = []

            for row in csv_reader:
                # Extract data from each row
                partner_name_csv = row.get('partner')
                source_document_csv = row.get('source_document') if row.get('source_document') else False
                scheduled_date_csv = datetime.strptime(row.get('scheduled_date'), '%d/%m/%Y')
                company_csv = row.get('company')
                picking_type_csv = row.get('picking_type')
                product_code_csv = row.get('product_code')
                quantity_csv = row.get('quantity') if row.get('quantity') else 0
                branch_csv = row.get('branch')


                # Search for partner, company, locations, and products etc
                partner = self.env['res.partner'].sudo().search([('name', '=', partner_name_csv)], limit=1)
                if not partner:
                    raise UserError(f"Partner '{partner_name_csv}' not found.")

                company = self.env['res.company'].sudo().search([('name', '=', company_csv)], limit=1)
                if not company:
                    raise UserError(f"Company '{company_csv}' not found.")

                branch = self.env['res.branch'].sudo().search([('name', '=', branch_csv)], limit=1)
                if not branch:
                    raise UserError(f"Branch '{branch_csv}' not found.")

                picking_type = self.env['stock.picking.type'].sudo().browse(int(picking_type_csv))
                if not picking_type:
                    raise UserError(f"Picking type '{picking_type_csv}' not found.")

                product = self.env['product.product'].sudo().search([('default_code', '=', product_code_csv)], limit=1)
                if not product:
                    raise UserError(f"Product code '{product_code_csv}' not found.")


                is_duplicate = [x for x in picking_dict if x['picking_type_id'] == picking_type.id]
                if is_duplicate:

                    for x in picking_dict:
                        if x['picking_type_id'] == picking_type.id:
                            x['move_ids_without_package'].append((0, 0, {
                                'product_id': product.id,
                                'product_uom_qty': quantity_csv,
                                'initial_demand': quantity_csv,
                                'name': product.name,
                                'product_uom': product.uom_id.id
                            }))

                else:
                    # Otherwise, create a new picking record
                    if picking_type.code == 'incoming':
                        location = picking_type.warehouse_id._get_partner_locations()[1].id
                        destination_location = picking_type.default_location_dest_id.id
                    elif picking_type.code == 'outgoing':
                        location = picking_type.default_location_src_id.id
                        destination_location = picking_type.warehouse_id._get_partner_locations()[0].id

                    # print('PICKING TYPE CODE', picking_type.code, 'LOCATION', location, 'DESTINATION', destination_location)
                    
                    data = {
                        'is_from_import': True,
                        'partner_id': partner.id,
                        'origin': source_document_csv,
                        'branch_id': branch.id,
                        'location_id': location,
                        'scheduled_date': scheduled_date_csv,
                        'location_dest_id': destination_location,
                        'picking_type_id': picking_type.id,
                        'company_id': company.id,
                        'state': 'draft',
                        'move_ids_without_package': [(0, 0, {
                            'product_id': product.id,
                            'product_uom_qty': quantity_csv,
                            'initial_demand': quantity_csv,
                            'name': product.name,
                            'product_uom': product.uom_id.id
                        })],
                    }
                    picking_dict.append(data)
            picking = self.env['stock.picking'].sudo().create(picking_dict)

        except Exception as e:
            raise UserError(f"An error occurred during CSV import: {str(e)}")
