# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime, date


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT 
                  ru.id AS user_id,
                  COALESCE(ru.package_unlink_data, '') AS package_unlink_data
                FROM
                  res_users as ru
                WHERE 
                  ru.active != FALSE	AND ru.share = FALSE
                ORDER BY 
                  user_id asc
            '''
            self.env.cr.execute(query)
            users_data = self.env.cr.dictfetchall()
            for record in users_data:
                user_id = record.get('user_id')
                old_value = record.get('package_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET package_unlink_data =%s WHERE id =%s""",(new_value, user_id))
                self._cr.commit()
        return res

    def get_stock_quant_package_data(self):
        query = '''
                SELECT
                    sqp.id AS package_id,
                    sqp.name,
                    sqp.package_status AS state,
                    COALESCE(sqp.package_expiration_date_time::TEXT, '') AS expiration_date,
                    COALESCE(sl.id, 0) AS location_id,
                    COALESCE(sl.complete_name, '') AS location,
                    COALESCE(pp.id, 0) AS package_type_id,
                    COALESCE(pp.name, '') AS package_type,
                    CASE 
                        WHEN sqp.package_status = 'packed' THEN 'Packed'
                        WHEN sqp.package_status = 'partial' THEN 'Partial'
                        WHEN sqp.package_status = 'empty' THEN 'Empty'
                        ELSE sqp.package_status
                    END AS status,
                    CASE 
                        WHEN sqp.package_status = 'packed' THEN '#008000'
                        WHEN sqp.package_status = 'partial' THEN '#33A961'
                        WHEN sqp.package_status = 'empty' THEN '#82C7D2'
                        ELSE '#FFA500'
                    END AS color
                FROM
                    stock_quant_package sqp
                    LEFT JOIN product_packaging pp ON (sqp.packaging_id = pp.id)
                    LEFT JOIN stock_location sl ON (sqp.location_id = sl.id) 
                WHERE 
                    sqp.id is not null
                group by
                sqp.id, sl.id, pp.id
                ORDER BY package_id desc
            '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.package_date = datetime.now()
        return result

    def get_stock_quant_package_line_data(self):
        query = '''
            SELECT 
                sq.id AS quant_id,
                sqp.id AS package_id,
                pp.id AS product_id,
                CONCAT('[', pp.default_code, '] ', pt.name) AS product,
                COALESCE(pp.barcode, '') AS barcode, 
                COALESCE(pp.default_code, '') AS item_no,
                pt.tracking,
                COALESCE(sq.quantity, 0.0) AS qty,
                COALESCE(uu.id, 0) AS product_uom_id,
                COALESCE(uu.name, '') AS product_uom
            FROM
                stock_quant sq
                LEFT JOIN stock_quant_package sqp ON (sq.package_id = sqp.id)
                LEFT JOIN product_product pp ON (sq.product_id = pp.id) 
                LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                LEFT JOIN uom_uom uu ON (pt.uom_id = uu.id)
            WHERE
                sq.package_id is not null
            ORDER BY quant_id asc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.package_line_date = datetime.now()
        return result

    def get_dynamic_stock_quant_package_data(self):
        sqp_datetime = self.env.user.package_date or datetime.now()
        query = '''
                SELECT
                    sqp.id AS package_id,
                    sqp.name,
                    sqp.package_status AS state,
                    COALESCE(sqp.package_expiration_date_time::TEXT, '') AS expiration_date,
                    COALESCE(sl.id, 0) AS location_id,
                    COALESCE(sl.complete_name, '') AS location,
                    COALESCE(pp.id, 0) AS package_type_id,
                    COALESCE(pp.name, '') AS package_type,
                    CASE 
                        WHEN sqp.package_status = 'packed' THEN 'Packed'
                        WHEN sqp.package_status = 'partial' THEN 'Partial'
                        WHEN sqp.package_status = 'empty' THEN 'Empty'
                        ELSE sqp.package_status
                    END AS status,
                    CASE 
                        WHEN sqp.package_status = 'packed' THEN '#008000'
                        WHEN sqp.package_status = 'partial' THEN '#33A961'
                        WHEN sqp.package_status = 'empty' THEN '#82C7D2'
                        ELSE '#FFA500'
                    END AS color
                FROM
                    stock_quant_package sqp
                    LEFT JOIN product_packaging pp ON (sqp.packaging_id = pp.id)
                    LEFT JOIN stock_location sl ON (sqp.location_id = sl.id) 
                WHERE 
                    sqp.id is not null AND sqp.write_date >= '%s' OR sqp.create_date >= '%s'
                group by
                sqp.id, sl.id, pp.id
                ORDER BY package_id desc
            '''%(sqp_datetime, sqp_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.package_date = datetime.now()
        return result

    def get_dynamic_stock_quant_package_line_data(self):
        sq_datetime = self.env.user.package_line_date or datetime.now()
        query = '''
            SELECT 
                sq.id AS quant_id,
                sqp.id AS package_id,
                pp.id AS product_id,
                CONCAT('[', pp.default_code, '] ', pt.name) AS product,
                COALESCE(pp.barcode, '') AS barcode, 
                COALESCE(pp.default_code, '') AS item_no,
                pt.tracking,
                COALESCE(sq.quantity, 0.0) AS qty,
                COALESCE(uu.id, 0) AS product_uom_id,
                COALESCE(uu.name, '') AS product_uom
            FROM
                stock_quant sq
                LEFT JOIN stock_quant_package sqp ON (sq.package_id = sqp.id)
                LEFT JOIN product_product pp ON (sq.product_id = pp.id) 
                LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                LEFT JOIN uom_uom uu ON (pt.uom_id = uu.id)
            WHERE
                sq.package_id is not null AND sq.write_date >= '%s' OR sq.create_date >= '%s'
            ORDER BY quant_id asc
        '''%(sq_datetime, sq_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.package_line_date = datetime.now()
        return result

    def get_package_list(self, sort='id desc'):
        data_list = []
        status_dict = {'packed': 'Packed', 'partial': 'Partial'}
        color_dict = {'partial': '#33A961', 'packed': '#008000'}
        domain = [('location_id', '!=', False), ('location_id.usage', '=', 'internal')];
        for package_id in self.env['stock.quant.package'].search(domain, order=sort):
            vals = {}
            vals['package_id'] = package_id.id
            vals['name'] = package_id.name
            vals['state'] = package_id.package_status if package_id.package_status else ''
            vals['status'] = status_dict.get(package_id.package_status, '')
            vals['color'] = color_dict.get(package_id.package_status, '')
            vals['package_type_id'] = package_id.packaging_id.id if package_id.packaging_id else 0
            vals['package_type'] = package_id.packaging_id.name if package_id.packaging_id else ''
            vals['expiration_date'] = str(package_id.package_expiration_date_time) if package_id.package_expiration_date_time else ''
            vals['location_id'] = package_id.location_id.id if package_id.location_id else 0
            vals['location'] = package_id.location_id.display_name if package_id.location_id else ''
            data_list.append(vals)
        return data_list

    def get_package_data(self):
        self.ensure_one()
        data_list = []
        for quant_id in self.quant_ids:
            vals = {}
            product_id = quant_id.product_id
            vals['quant_id'] = quant_id.id
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['qty'] = quant_id.quantity
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['tracking'] = product_id.tracking
            vals['product_uom_id'] = quant_id.product_uom_id.id if quant_id.product_uom_id else 0
            vals['product_uom'] = quant_id.product_uom_id.name if quant_id.product_uom_id else ''
            data_list.append(vals)
        return data_list

    # Master Record Api
    def get_package_data(self):
        query = '''
        SELECT
           sqp.id as package_id,
           sqp.name as package_name,
           sqp.location_id as location_id
        FROM
           stock_quant_package as sqp
        WHERE
           sqp.id != 0
        ORDER BY
           package_id desc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.stock_package_date = datetime.now()
        return result

    def get_dynamic_package_data(self):
        package_datetime = self.env.user.stock_package_date or datetime.now()
        query = '''
        SELECT
           sqp.id as package_id,
           sqp.name as package_name,
           sqp.location_id as location_id
        FROM
           stock_quant_package as sqp
        WHERE
           sqp.id != 0 AND sqp.write_date >= '%s' OR sqp.create_date >= '%s'
        ORDER BY
           package_id desc
        '''%(package_datetime, package_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.stock_package_date = datetime.now()
        return result