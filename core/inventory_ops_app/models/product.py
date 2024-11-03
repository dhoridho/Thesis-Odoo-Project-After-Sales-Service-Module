# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_products_data(self):
        query = '''
           SELECT
               pp.id AS product_id,
               pt.name AS product,
               pt.type AS product_type,
               COALESCE(pp.default_code, '') AS item_no,
               COALESCE(pp.barcode, '') AS barcode,
               pt.tracking,
               COALESCE(uu.id, 0) AS uom_id,
               COALESCE(uu.name, '') AS uom,
               COALESCE(uc.id, 0) AS category_id,
               COALESCE(uc.name, '') AS category,
               COALESCE(CAST(
               (
                  select 
                    json_agg(
                      json_build_object(
                        'id', COALESCE(spl.id, 0), 
                        'name', COALESCE(spl.name, '')
                      )
                    ) lot_serial 
                  from 
                    stock_production_lot as spl 
                    --LEFT JOIN res_company rc ON (spl.company_id = rc.id)
                    WHERE 
                    spl.product_id = pp.id 
               ) AS text), '[]') AS lot_serial_list,
               COALESCE(CAST(
               (
                  select 
                    json_agg(
                      json_build_object(
                         'multi_barcode', COALESCE(ptb.name, ''),
                         'uom_id', COALESCE(uu.id, 0), 
                         'uom', COALESCE(uu.name, '')
                      )
                    ) multi_barcode_uom 
                  from 
                    product_template_barcode as ptb 
                    LEFT JOIN uom_uom uu ON (ptb.uom_id = uu.id)
                    WHERE 
                    ptb.product_id = pp.id 
               ) AS text), '[]') AS multi_barcode_jsonarray,
               COALESCE(pp.multi_barcode, FALSE) AS multi_barcode,
               concat('[',CONCAT(
                (
                  SELECT 
                    ARRAY_TO_STRING(ARRAY_AGG(DISTINCT ptb.name), ',')
                  FROM 
                    product_template_barcode as ptb 
                  WHERE 
                    ptb.product_id = pp.id 
                ), 
                ''
               ),']') AS multi_barcode_stringlist
           FROM
              product_product as pp
              LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
              LEFT JOIN uom_uom uu ON (pt.uom_id = uu.id)
              LEFT JOIN uom_category uc ON (uu.category_id = uc.id)
           WHERE
              pp.id != 0 AND pp.active != false
           ORDER BY 
               product_id desc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.product_date = datetime.now()
        return result

    def get_dynamic_products_data(self):
        product_datetime = self.env.user.product_date or datetime.now()
        query = '''
           SELECT
               pp.id AS product_id,
               pt.name AS product, 			   
               pt.type AS product_type,
               COALESCE(pp.default_code, '') AS item_no,
               COALESCE(pp.barcode, '') AS barcode,
               pt.tracking,
               COALESCE(uu.id, 0) AS uom_id,
               COALESCE(uu.name, '') AS uom,
               COALESCE(uc.id, 0) AS category_id,
               COALESCE(uc.name, '') AS category,
               COALESCE(CAST(
               (
                  select 
                    json_agg(
                      json_build_object(
                        'id', COALESCE(spl.id, 0), 
                        'name', COALESCE(spl.name, '')
                      )
                    ) lot_serial 
                  from 
                    stock_production_lot as spl 
                    --LEFT JOIN res_company rc ON (spl.company_id = rc.id)
                    WHERE 
                    spl.product_id = pp.id 
               ) AS text), '[]') AS lot_serial_list,
               COALESCE(CAST(
               (
                  select 
                    json_agg(
                      json_build_object(
                         'multi_barcode', COALESCE(ptb.name, ''),
                         'uom_id', COALESCE(uu.id, 0), 
                         'uom', COALESCE(uu.name, '')
                      )
                    ) multi_barcode_uom 
                  from 
                    product_template_barcode as ptb 
                    LEFT JOIN uom_uom uu ON (ptb.uom_id = uu.id)
                    WHERE 
                    ptb.product_id = pp.id 
               ) AS text), '[]') AS multi_barcode_jsonarray,
               COALESCE(pp.multi_barcode, FALSE) AS multi_barcode,
               concat('[',CONCAT(
                (
                  SELECT 
                    ARRAY_TO_STRING(ARRAY_AGG(DISTINCT ptb.name), ',')
                  FROM 
                    product_template_barcode as ptb 
                  WHERE 
                    ptb.product_id = pp.id 
                ), 
                ''
               ),']') AS multi_barcode_stringlist
           FROM
              product_product as pp
              LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
              LEFT JOIN uom_uom uu ON (pt.uom_id = uu.id)
              LEFT JOIN uom_category uc ON (uu.category_id = uc.id)
           WHERE
              pp.id != 0 AND pp.active != false AND pp.write_date >= '%s' OR pp.create_date >= '%s'
           ORDER BY 
               product_id desc
        '''%(product_datetime,product_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.product_date = datetime.now()
        return result

    def search_product(self, arg):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            barcode_id = self.env['product.template.barcode'].search([('name', '=', str(arg))], limit=1)
            product_id = barcode_id and barcode_id.product_id or False
        if not product_id:
            product_id = self.env['product.product'].search([('default_code', '=', str(arg))], limit=1)
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['item_no'] = product_id.default_code or ''
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            vals['uom_id'] = product_id.uom_id.id if product_id.uom_id else 0
            vals['uom'] = product_id.uom_id.name if product_id.uom_id else ''
            vals['multi_barcode'] = product_id.multi_barcode
            multi_barcode_list = []
            multi_barcode_data = []
            for record in self.env['product.template.barcode'].search([('product_id', '=', product_id.id)]):
                multi_barcode_list.append(record.name)
                multi_vals = {}
                multi_vals['multi_barcode'] = record.name
                multi_vals['uom_id'] = record.uom_id.id if record.uom_id else 0
                multi_vals['uom'] = record.uom_id.name if record.uom_id else ''
                multi_barcode_data.append(multi_vals)
            vals['multi_barcode_stringlist'] = multi_barcode_list
            vals['multi_barcode_jsonarray'] = multi_barcode_data
            product_list.append(vals)
        else:
            for product_id in self.env['product.product'].search([('name', 'ilike', str(arg))]):
                vals = {}
                vals['product_id'] = product_id.id
                vals['product'] = product_id.name
                vals['item_no'] = product_id.default_code or ''
                vals['barcode'] = product_id.barcode or ''
                vals['tracking'] = product_id.tracking
                vals['uom_id'] = product_id.uom_id.id if product_id.uom_id else 0
                vals['uom'] = product_id.uom_id.name if product_id.uom_id else ''
                vals['multi_barcode'] = product_id.multi_barcode
                multi_barcode_list = []
                multi_barcode_data = []
                for record in self.env['product.template.barcode'].search([('product_id', '=', product_id.id)]):
                    multi_barcode_list.append(record.name)
                    multi_vals = {}
                    multi_vals['multi_barcode'] = record.name
                    multi_vals['uom_id'] = record.uom_id.id if record.uom_id else 0
                    multi_vals['uom'] = record.uom_id.name if record.uom_id else ''
                    multi_barcode_data.append(multi_vals)
                vals['multi_barcode_stringlist'] = multi_barcode_list
                vals['multi_barcode_jsonarray'] = multi_barcode_data
                product_list.append(vals)
        return product_list

    def search_product_barcode(self, arg):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            barcode_id = self.env['product.template.barcode'].search([('name', '=', str(arg))], limit=1)
            product_id = barcode_id and barcode_id.product_id or False
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['item_no'] = product_id.default_code or ''
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            vals['uom_id'] = product_id.uom_id.id if product_id.uom_id else 0
            vals['uom'] = product_id.uom_id.name if product_id.uom_id else ''
            vals['multi_barcode'] = product_id.multi_barcode
            multi_barcode_list = []
            multi_barcode_data = []
            for record in self.env['product.template.barcode'].search([('product_id', '=', product_id.id)]):
                multi_barcode_list.append(record.name)
                multi_vals = {}
                multi_vals['multi_barcode'] = record.name
                multi_vals['uom_id'] = record.uom_id.id if record.uom_id else 0
                multi_vals['uom'] = record.uom_id.name if record.uom_id else ''
                multi_barcode_data.append(multi_vals)
            vals['multi_barcode_stringlist'] = multi_barcode_list
            vals['multi_barcode_jsonarray'] = multi_barcode_data
            product_list.append(vals)
        return product_list

    def app_search_product(self, arg, company_id):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            barcode_id = self.env['product.template.barcode'].search([('name', '=', str(arg))], limit=1)
            product_id = barcode_id and barcode_id.product_id or False
        if not product_id:
            product_id = self.env['product.product'].search([('default_code', '=', str(arg))], limit=1)
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['tracking'] = product_id.tracking
            vals['category_id'] = product_id.uom_id.category_id.id if product_id.uom_id.category_id else False
            vals['uom_id'] = product_id.uom_id.id if product_id.uom_id else 0
            vals['uom'] = product_id.uom_id.name if product_id.uom_id else ''

            list_lot_serial = []
            for record in self.env['stock.production.lot'].search([('product_id', '=', product_id.id), ('company_id', '=', company_id)]):
                lot_vals = {}
                lot_vals['id'] = record.id
                lot_vals['name'] = record.name
                list_lot_serial.append(lot_vals)
            vals['lot_serial_list'] = list_lot_serial

            vals['multi_barcode'] = product_id.multi_barcode
            multi_barcode_list = []
            multi_barcode_data = []
            for record in self.env['product.template.barcode'].search([('product_id', '=', product_id.id)]):
                multi_barcode_list.append(record.name)
                multi_vals = {}
                multi_vals['multi_barcode'] = record.name
                multi_vals['uom_id'] = record.uom_id.id if record.uom_id else 0
                multi_vals['uom'] = record.uom_id.name if record.uom_id else ''
                multi_barcode_data.append(multi_vals)
            vals['multi_barcode_stringlist'] = multi_barcode_list
            vals['multi_barcode_jsonarray'] = multi_barcode_data
            product_list.append(vals)
        else:
            for product_id in self.env['product.product'].search([('name', 'ilike', str(arg))]):
                vals = {}
                vals['product_id'] = product_id.id
                vals['product'] = product_id.name
                vals['barcode'] = product_id.barcode or ''
                vals['item_no'] = product_id.default_code or ''
                vals['tracking'] = product_id.tracking
                vals['category_id'] = product_id.uom_id.category_id.id if product_id.uom_id.category_id else False
                vals['uom_id'] = product_id.uom_id.id if product_id.uom_id else 0
                vals['uom'] = product_id.uom_id.name if product_id.uom_id else ''

                list_lot_serial = []
                for record in self.env['stock.production.lot'].search(
                        [('product_id', '=', product_id.id), ('company_id', '=', company_id)]):
                    lot_vals = {}
                    lot_vals['id'] = record.id
                    lot_vals['name'] = record.name
                    list_lot_serial.append(lot_vals)

                vals['lot_serial_list'] = list_lot_serial
                vals['multi_barcode'] = product_id.multi_barcode
                multi_barcode_list = []
                multi_barcode_data = []
                for record in self.env['product.template.barcode'].search([('product_id', '=', product_id.id)]):
                    multi_barcode_list.append(record.name)
                    multi_vals = {}
                    multi_vals['multi_barcode'] = record.name
                    multi_vals['uom_id'] = record.uom_id.id if record.uom_id else 0
                    multi_vals['uom'] = record.uom_id.name if record.uom_id else ''
                    multi_barcode_data.append(multi_vals)
                vals['multi_barcode_stringlist'] = multi_barcode_list
                vals['multi_barcode_jsonarray'] = multi_barcode_data
                product_list.append(vals)
        return product_list

    def app_search_product_barcode(self, arg, company_id):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            barcode_id = self.env['product.template.barcode'].search([('name', '=', str(arg))], limit=1)
            product_id = barcode_id and barcode_id.product_id or False
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['tracking'] = product_id.tracking
            vals['category_id'] = product_id.uom_id.category_id.id if product_id.uom_id.category_id else False
            vals['uom_id'] = product_id.uom_id.id if product_id.uom_id else 0
            vals['uom'] = product_id.uom_id.name if product_id.uom_id else ''

            list_lot_serial = []
            for record in self.env['stock.production.lot'].search([('product_id', '=', product_id.id), ('company_id', '=', company_id)]):
                lot_vals = {}
                lot_vals['id'] = record.id
                lot_vals['name'] = record.name
                list_lot_serial.append(lot_vals)
            vals['lot_serial_list'] = list_lot_serial

            vals['multi_barcode'] = product_id.multi_barcode
            multi_barcode_list = []
            multi_barcode_data = []
            for record in self.env['product.template.barcode'].search([('product_id', '=', product_id.id)]):
                multi_barcode_list.append(record.name)
                multi_vals = {}
                multi_vals['multi_barcode'] = record.name
                multi_vals['uom_id'] = record.uom_id.id if record.uom_id else 0
                multi_vals['uom'] = record.uom_id.name if record.uom_id else ''
                multi_barcode_data.append(multi_vals)
            vals['multi_barcode_stringlist'] = multi_barcode_list
            vals['multi_barcode_jsonarray'] = multi_barcode_data
            product_list.append(vals)
        return product_list

    def get_product_info(self, arg):
        if self.env.user.company_id.sudo().sh_product_barcode_mobile_type == "barcode":
            domain = [("barcode", "=", str(arg))]
        elif self.env.user.company_id.sudo().sh_product_barcode_mobile_type == "int_ref":
            domain = [("default_code", "=", str(arg))]

        elif self.env.user.company_id.sudo().sh_product_barcode_mobile_type == "sh_qr_code":
            domain = [("sh_qr_code", "=", str(arg))]

        elif self.env.user.company_id.sudo().sh_product_barcode_mobile_type == "all":
            domain = ["|", "|", ("default_code", "=", str(arg)), ("barcode", "=", str(arg)), ("sh_qr_code", "=", str(arg))]

        product_id = self.env['product.product'].search(domain, limit=1)
        if not product_id:
            barcode_id = self.env['product.template.barcode'].search([('name', '=', str(arg))], limit=1)
            product_id = barcode_id and barcode_id.product_id or False
        vals = {}
        if product_id:
            vals['product_id'] = product_id.id
            default_code = product_id.default_code if product_id.default_code else ''
            vals['product'] = '[' + default_code  + '] ' + product_id.name
            vals['product_type'] = product_id.type
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            vals['internal_reference'] = product_id.default_code or ''
            vals['sale_price'] = product_id.lst_price or 0.00
            if product_id.type == 'product':
                vals['onhand_qty'] = product_id.qty_available
                vals['forecast_qty'] = product_id.virtual_available
            quant_ids = self.env['stock.quant'].search([('product_id', '=', product_id.id), ('location_id.usage', '=', 'internal')])
            line_list_vals = []
            product_line_data = []
            for line in quant_ids:
                line_list_vals.append({
                    'product_id': line.product_id,
                    'location_id': line.location_id.id,
                    'location': line.location_id.complete_name,
                    'value': [line.value],
                    'available_quantity': [line.available_quantity],
                    'on_hand_qty': [line.quantity],
                    'product_uom_id': line.product_uom_id.id,
                    'product_uom': line.product_uom_id.name,
                    'company_id': line.company_id.id,
                })
            for final_line in line_list_vals:
                final_line.pop('product_id')
                final_line['available_quantity'] = sum(final_line['available_quantity'])
                final_line['on_hand_qty'] = sum(final_line['on_hand_qty'])
                final_line['value'] = sum(final_line['value'])
                product_line_data.append(final_line)
            vals['product_line_data'] = product_line_data
            vals['error_message'] = "success"
        else:
            if self.env.user.company_id.sudo().sh_product_bm_is_notify_on_fail:
                error_message = "Scanned Internal Reference/Barcode not exist in any product!"
                vals['error_message'] = error_message
        return vals


class ProductCategory(models.Model):
    _inherit = 'product.category'

    def get_product_category_data(self):
        query = '''
            SELECT
               pc.id AS product_category_id,
               pc.complete_name AS product_category
            FROM 
               product_category as pc
            WHERE
               pc.name != ''
            ORDER BY 
               product_category_id desc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.product_category_date = datetime.now()
        return result

    def get_dynamic_product_category_data(self):
        product_category_datetime = self.env.user.product_category_date or datetime.now()
        query = '''
            SELECT
               pc.id AS product_category_id,
               pc.complete_name AS product_category
            FROM 
               product_category as pc
            WHERE
               pc.name != '' AND pc.write_date >= '%s' OR pc.create_date >= '%s'
            ORDER BY 
               product_category_id desc
        '''%(product_category_datetime, product_category_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.product_category_date = datetime.now()
        return result


class ProductTemplateBarcode(models.Model):
    _inherit = 'product.template.barcode'

    def get_product_template_barcode_data(self):
        query = '''
           SELECT
              ptb.id AS product_template_barcode_id,
              ptb.name AS barcode,
              COALESCE(pp.id, 0) AS product_id,
              COALESCE(pp.product_display_name, '') AS product,
              COALESCE(uu.id, 0) AS uom_id,
              COALESCE(uu.name, '') AS uom
           FROM 
              product_template_barcode as ptb
              LEFT JOIN product_product pp ON (ptb.product_id = pp.id) 
              LEFT JOIN uom_uom uu ON (ptb.uom_id = uu.id) 
           WHERE
              ptb.id != 0
           ORDER BY 
              product_template_barcode_id asc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.product_template_barcode_date = datetime.now()
        return result

    def get_dynamic_product_template_barcode_data(self):
        product_template_barcode_datetime = self.env.user.product_template_barcode_date or datetime.now()
        query = '''
           SELECT
              ptb.id AS product_template_barcode_id,
              ptb.name AS barcode,
              COALESCE(pp.id, 0) AS product_id,
              COALESCE(pp.product_display_name, '') AS product,
              COALESCE(uu.id, 0) AS uom_id,
              COALESCE(uu.name, '') AS uom
           FROM 
              product_template_barcode as ptb
              LEFT JOIN product_product pp ON (ptb.product_id = pp.id) 
              LEFT JOIN uom_uom uu ON (ptb.uom_id = uu.id) 
           WHERE
              ptb.id != 0 AND ptb.write_date >= '%s' OR ptb.create_date >= '%s'
           ORDER BY 
              product_template_barcode_id asc
        '''%(product_template_barcode_datetime, product_template_barcode_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.product_template_barcode_date = datetime.now()
        return result