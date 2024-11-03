# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from datetime import datetime, date


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    # app_line_ids = fields.One2many('stock.inventory.line.app', 'inventory_id', string='Lines')

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT 
                  ru.id AS user_id,
                  COALESCE(ru.stock_count_unlink_data, '') AS stock_count_unlink_data
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
                old_value = record.get('stock_count_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET stock_count_unlink_data =%s WHERE id =%s""", (new_value, user_id))
                self._cr.commit()
        return res

    def get_locations_data(self):
        location_list = []
        if len(self.location_ids.ids) != 0:
            location_data = self.env["stock.location"].search([('company_id', '=', self.company_id.id),
                                                           ('usage', 'in', ['internal', 'transit']),
                                                           ('id', 'child_of', self.location_ids.ids)])
            for record in location_data:
                dict_vals = {}
                dict_vals['id'] = record.id
                dict_vals['name'] = record.name_get()[0][1]
                location_list.append(dict_vals)
        return str(location_list)

    def get_inventory_data(self):
        query = '''
            SELECT 
                si.id AS inventory_id, 
                si.name,
                si.state,
                si.company_id,
                si.create_date AS create_date,
                COALESCE(si.exhausted, false) AS exhausted,
                date(si.create_date) AS date_filtered, 
                COALESCE(si.inv_ref, '') AS inv_ref,
                COALESCE(sw.name, '') AS sc_warehouse,
                COALESCE(sw.id, 0) AS sc_warehouse_id, 
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT sl.complete_name), ', ') AS locations,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT pc.complete_name), ', ') AS product_category,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT CONCAT('[' || pt.default_code || '] ' || pt.name)), ', ') AS products,
                concat('[',ARRAY_TO_STRING(ARRAY_AGG(DISTINCT pc.id), ','), ']') AS product_category_ids,
                concat('[',ARRAY_TO_STRING(ARRAY_AGG(DISTINCT pp.id), ','), ']') AS products_ids,
                CASE
                   WHEN si.inventoried_product = 'all_product' THEN 'All Products'
                   WHEN si.inventoried_product = 'specific_product' THEN 'Specific Products'
                   WHEN si.inventoried_product = 'specific_category' THEN 'Specific Categories'
                   ELSE COALESCE(si.inventoried_product, '')
                END AS inventoried_product, 
                CASE 
                   WHEN si.prefill_counted_quantity = 'counted' THEN 'Default to stock on hand'
                   WHEN si.prefill_counted_quantity = 'zero' THEN 'Default to zero'
                END AS prefill_counted_quantity,
                CASE
                    WHEN si.state = 'draft' THEN 'Draft'
                    WHEN si.state = 'confirm' THEN 'In Progress'
                    WHEN si.state = 'completed' THEN 'Completed'
                    WHEN si.state = 'to_approve' THEN 'Waiting for Approval'
                    WHEN si.state = 'approved' THEN 'Approved'
                    WHEN si.state = 'done' THEN 'Done'
                    ELSE si.state
                END AS status,
                CASE
                    WHEN si.state = 'draft' THEN '#82C7D2'
                    WHEN si.state = 'confirm' THEN '#92c422'
                    WHEN si.state = 'completed' THEN '#008000'
                    WHEN si.state = 'to_approve' THEN '#efb139'
                    WHEN si.state = 'approved' THEN '#008000'
                    WHEN si.state = 'done' THEN '#262628'
                    ELSE '#FFA500'
                END AS color
                FROM 
                stock_inventory si
                LEFT JOIN stock_inventory_stock_location_rel sislr ON (si.id = sislr.stock_inventory_id) 
                LEFT JOIN stock_location sl ON (sislr.stock_location_id = sl.id) 
                LEFT JOIN product_product_stock_inventory_rel ppsir ON (si.id = ppsir.stock_inventory_id) 
                LEFT JOIN product_product pp ON (ppsir.product_product_id = pp.id) 
                LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                LEFT JOIN category_id pcsir ON (si.id = pcsir.p_id) 
                LEFT JOIN product_category pc ON (pcsir.product_category_id = pc.id) 
                LEFT JOIN stock_warehouse sw ON (si.warehouse_id = sw.id)
                WHERE si.state NOT IN ('cancel', 'rejected')
                group by
                si.id, sw.id
                ORDER BY inventory_id desc
            '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        for count in range(len(result)):
            record = result[count]
            inventory_id = record.get('inventory_id')
            inv_rec = self.env["stock.inventory"].browse(inventory_id)
            location_data = inv_rec.sudo().get_locations_data()
            result[count]["location_ids"] = location_data
        self.env.user.stock_count_date = datetime.now()
        return result

    def get_inventory_line_data(self):
        query = '''
            SELECT
                 sil.id AS line_id,
                 sil.inventory_id AS stock_count_id,
                 pp.id AS product_id,
                 CONCAT('[', pp.default_code, '] ', pt.name) AS product,
                 COALESCE(sil.temp_barcode, '') AS barcode, 
                 COALESCE(pp.multi_barcode, FALSE) AS multi_barcode,
                 COALESCE(pp.default_code, '') AS item_no,
                 COALESCE(sil.product_qty, 0.0) AS scanned_qty,
                 COALESCE(sil.product_qty, 0.0) AS previous_qty,
                 COALESCE(sl.id, 0) AS location_id,
                 COALESCE(sl.complete_name, '') AS location,
                 COALESCE(spl.name, '') AS lot_name,
                 pt.tracking,
                 COALESCE(uu.id, 0) AS product_uom_id,
                 COALESCE(uu.name, '') AS product_uom,
                 COALESCE(uu2.id, 0) AS uom_id,
                 COALESCE(uu2.name, '') AS uom,
                 COALESCE(uc.id, 0) AS category_uom_id,
                 COALESCE(sqp.name, '') AS pack
                 FROM
                 stock_inventory_line sil
                 LEFT JOIN product_product pp ON (sil.product_id = pp.id) 
                 LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id) 
                 LEFT JOIN stock_location sl ON (sil.location_id = sl.id)
                 LEFT JOIN stock_production_lot spl ON (sil.prod_lot_id = spl.id)
                 LEFT JOIN uom_uom uu ON (sil.product_uom_id = uu.id)
                 LEFT JOIN uom_uom uu2 ON (sil.uom_id = uu2.id)
                 LEFT JOIN uom_category uc ON (uu2.category_id = uc.id)
                 LEFT JOIN stock_quant_package sqp ON (sil.package_id = sqp.id)
                 LEFT JOIN stock_inventory si ON (sil.inventory_id = si.id) 
                 WHERE
                 sil.inventory_id is not null AND
                 si.state NOT IN ('cancel', 'rejected')
                 ORDER BY line_id asc
            '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.stock_count_line_date = datetime.now()
        return result

    # Dynamic api call
    def get_dynamic_inventory_data(self):
        si_datetime = self.env.user.stock_count_date or datetime.now()
        query = '''
            SELECT 
                si.id AS inventory_id, 
                si.name,
                si.state,
                si.company_id,
                si.create_date AS create_date,
                COALESCE(si.exhausted, false) AS exhausted,
                date(si.create_date) AS date_filtered, 
                COALESCE(si.inv_ref, '') AS inv_ref, 
                COALESCE(sw.name, '') AS sc_warehouse,
                COALESCE(sw.id, 0) AS sc_warehouse_id,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT sl.complete_name), ', ') AS locations,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT pc.complete_name), ', ') AS product_category,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT CONCAT('[' || pt.default_code || '] ' || pt.name)), ', ') AS products,
                concat('[',ARRAY_TO_STRING(ARRAY_AGG(DISTINCT pc.id), ','), ']') AS product_category_ids,
                concat('[',ARRAY_TO_STRING(ARRAY_AGG(DISTINCT pp.id), ','), ']') AS products_ids,
                CASE
                   WHEN si.inventoried_product = 'all_product' THEN 'All Products'
                   WHEN si.inventoried_product = 'specific_product' THEN 'Specific Products'
                   WHEN si.inventoried_product = 'specific_category' THEN 'Specific Categories'
                   ELSE COALESCE(si.inventoried_product, '')
                END AS inventoried_product,
                CASE 
                   WHEN si.prefill_counted_quantity = 'counted' THEN 'Default to stock on hand'
                   WHEN si.prefill_counted_quantity = 'zero' THEN 'Default to zero'
                END AS prefill_counted_quantity, 
                CASE
                    WHEN si.state = 'draft' THEN 'Draft'
                    WHEN si.state = 'confirm' THEN 'In Progress'
                    WHEN si.state = 'completed' THEN 'Completed'
                    WHEN si.state = 'to_approve' THEN 'Waiting for Approval'
                    WHEN si.state = 'approved' THEN 'Approved'
                    WHEN si.state = 'done' THEN 'Done'
                    ELSE si.state
                END AS status,
                CASE
                    WHEN si.state = 'draft' THEN '#82C7D2'
                    WHEN si.state = 'confirm' THEN '#92c422'
                    WHEN si.state = 'completed' THEN '#008000'
                    WHEN si.state = 'to_approve' THEN '#efb139'
                    WHEN si.state = 'approved' THEN '#008000'
                    WHEN si.state = 'done' THEN '#262628'
                    ELSE '#FFA500'
                END AS color
                FROM 
                stock_inventory si
                LEFT JOIN stock_inventory_stock_location_rel sislr ON (si.id = sislr.stock_inventory_id) 
                LEFT JOIN stock_location sl ON (sislr.stock_location_id = sl.id) 
                LEFT JOIN product_product_stock_inventory_rel ppsir ON (si.id = ppsir.stock_inventory_id) 
                LEFT JOIN product_product pp ON (ppsir.product_product_id = pp.id) 
                LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                LEFT JOIN category_id pcsir ON (si.id = pcsir.p_id) 
                LEFT JOIN product_category pc ON (pcsir.product_category_id = pc.id) 
                LEFT JOIN stock_warehouse sw ON (si.warehouse_id = sw.id)
                WHERE si.write_date >= '%s' OR si.create_date >= '%s'
                group by
                si.id, sw.id
                ORDER BY inventory_id desc
        '''%(si_datetime,si_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            for count in range(len(result)):
                record = result[count]
                inventory_id = record.get('inventory_id')
                inv_rec = self.env["stock.inventory"].browse(inventory_id)
                location_data = inv_rec.sudo().get_locations_data()
                result[count]["location_ids"] = location_data
            self.env.user.stock_count_date = datetime.now()
        return result

    def get_dynamic_inventory_line_data(self):
        sil_datetime = self.env.user.stock_count_line_date or datetime.now()
        query = '''
            SELECT
                 sil.id AS line_id,
                 sil.inventory_id AS stock_count_id,
                 pp.id AS product_id,
                 CONCAT('[', pp.default_code, '] ', pt.name) AS product,
                 COALESCE(sil.temp_barcode, '') AS barcode, 
                 COALESCE(pp.multi_barcode, FALSE) AS multi_barcode,
                 COALESCE(pp.default_code, '') AS item_no,
                 COALESCE(sil.product_qty, 0.0) AS scanned_qty,
                 COALESCE(sil.product_qty, 0.0) AS previous_qty,
                 COALESCE(sl.id, 0) AS location_id,
                 COALESCE(sl.complete_name, '') AS location,
                 COALESCE(spl.name, '') AS lot_name,
                 pt.tracking,
                 COALESCE(uu.id, 0) AS product_uom_id,
                 COALESCE(uu.name, '') AS product_uom,
                 COALESCE(uu2.id, 0) AS uom_id,
                 COALESCE(uu2.name, '') AS uom,
                 COALESCE(uc.id, 0) AS category_uom_id,
                 COALESCE(sqp.name, '') AS pack
                 FROM
                 stock_inventory_line sil
                 LEFT JOIN product_product pp ON (sil.product_id = pp.id) 
                 LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id) 
                 LEFT JOIN stock_location sl ON (sil.location_id = sl.id)
                 LEFT JOIN stock_production_lot spl ON (sil.prod_lot_id = spl.id)
                 LEFT JOIN uom_uom uu ON (sil.product_uom_id = uu.id)
                 LEFT JOIN uom_uom uu2 ON (sil.uom_id = uu2.id)
                 LEFT JOIN uom_category uc ON (uu2.category_id = uc.id)
                 LEFT JOIN stock_quant_package sqp ON (sil.package_id = sqp.id)
                 LEFT JOIN stock_inventory si ON (sil.inventory_id = si.id)
                 WHERE
                 sil.inventory_id is not null AND sil.write_date >= '%s' OR sil.create_date >= '%s'
                 ORDER BY line_id asc
        '''%(sil_datetime,sil_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.stock_count_line_date = datetime.now()
        return result

    def get_count_list(self, sort='id asc', filter=False, start_date=False, end_date=False):
        data_list = []
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000','to_approve': '#efb139', 'approved': '#008000',
                      'done': '#262628'}
        if filter == 'done':
            domain = [('state', '=', 'done'), ('create_date', '>=', start_date), ('create_date', '<=', end_date)]
        else:
            domain = [('state', 'not in', ['cancel', 'rejected', 'done'])]
        for inventory_id in self.env['stock.inventory'].search(domain, order=sort):
            vals = {}
            vals['id'] = inventory_id.id
            vals['inv_ref'] = inventory_id.inv_ref
            vals['name'] = inventory_id.name
            vals['state'] = dict(inventory_id.fields_get(['state'])['state']['selection'])[inventory_id.state]
            vals['date'] = str(inventory_id.create_date)

            if inventory_id.inventoried_product != False:
                vals['inventoried_product'] = dict(inventory_id.fields_get(['inventoried_product'])['inventoried_product']['selection'])[inventory_id.inventoried_product]
            else:
                vals['inventoried_product'] = ''

            vals['color'] = color_dict.get(inventory_id.state, '')

            location_list = [record.name_get()[0][1] for record in list(set(inventory_id.location_ids))]
            vals['locations'] = ", ".join(location_list)

            list_data = []

            location_data = self.env["stock.location"].search([('company_id', '=', inventory_id.company_id.id),
                            ('usage', 'in', ['internal', 'transit']), ('id', 'child_of', inventory_id.location_ids.ids)])
            for record in location_data:
                dict_vals = {}
                dict_vals['id'] = record.id
                dict_vals['name'] = record.name_get()[0][1]
                list_data.append(dict_vals)
            vals['location_ids'] = list_data
            vals['company_id'] = inventory_id.company_id.id

            if inventory_id.inventoried_product == 'specific_product':
                product_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_ids))]
                vals['products'] = ", ".join(product_list)
                pro_list = []
                for rec in inventory_id.product_ids:
                    pro_list.append(rec.id)
                vals['products_ids'] = str(pro_list)
            else:
                vals['products'] = ""
                vals['products_ids'] = "[]"


            if inventory_id.inventoried_product == 'specific_category':
                product_category_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_categories))]
                vals['product_category'] = ", ".join(product_category_list)
                categ_list = []
                for rec in inventory_id.product_categories:
                    categ_list.append(rec.id)
                vals['product_category_ids'] = str(categ_list)
            else:
                vals['product_category'] = ""
                vals['product_category_ids'] = "[]"

            data_list.append(vals)
        return data_list

    def get_count_data(self):
        data_list = []
        for line in self.line_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['product_id'] = line.product_id.id
            vals['pack'] = line.package_id.name if line.package_id else ''
            vals['product'] = line.product_id.name
            vals['barcode'] = line.product_id.barcode or ''
            vals['item_no'] = line.product_id.default_code or ''
            vals['tracking'] = line.product_id.tracking
            vals['scanned_qty'] = line.product_qty
            vals['location_id'] = line.location_id.id
            vals['location'] = line.location_id.name_get()[0][1]
            vals['lot_name'] = line.prod_lot_id.name if line.prod_lot_id else ''
            vals['product_uom_id'] = line.product_uom_id.id
            vals['product_uom'] = line.product_uom_id.name
            vals['category_uom_id'] = line.product_id.uom_id.category_id.id if line.product_id.uom_id.category_id else 0
            vals['uom_id'] = line.uom_id.id if line.uom_id else 0
            vals['uom'] = line.uom_id.name if line.uom_id else ''
            data_list.append(vals)
        return data_list

    def create_stock_count_app(self, data_dict):
        vals = {}
        location_list = []
        analytic_groups_list = []
        product_list = []
        category_list = []
        vals['warehouse_id'] = data_dict.get('warehouse_id', False)
        vals['create_date'] = data_dict['count_date'] if data_dict.get('count_date', False) else str(datetime.now())[:19]
        location_list += [(int(record)) for record in data_dict['location_ids']]
        vals['location_ids'] = [(6,0,location_list)]
        analytic_groups_list += [(int(record)) for record in data_dict['analytic_tag_ids']]
        vals['analytic_tag_ids'] = [(6,0,analytic_groups_list)]
        vals['inventoried_product'] = data_dict['inventoried_product']
        vals['prefill_counted_quantity'] = data_dict['prefill_counted_quantity']
        vals['exhausted'] = data_dict['exhausted']
        if data_dict.get('product_ids', False):
            product_list += [(int(record)) for record in data_dict['product_ids']]
            vals['product_ids'] = [(6, 0, product_list)]
        elif data_dict.get('product_category', False):
            category_list += [(int(record)) for record in data_dict['product_category']]
            vals['product_categories'] = [(6, 0, category_list)]
        inventory_id = self.env['stock.inventory'].create(vals)

        vals2 = {}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        if inventory_id:
            vals2['inventory_id'] = inventory_id.id
            vals2['inv_ref'] = inventory_id.inv_ref
            vals2['name'] = inventory_id.name
            vals2['state'] = inventory_id.state
            vals2['status'] = dict(inventory_id.fields_get(['state'])['state']['selection'])[inventory_id.state]
            vals2['color'] = color_dict.get(inventory_id.state, '')
            vals2['date_filtered'] = str(inventory_id.create_date).split(" ")[0] if inventory_id.create_date else ""
            vals2['create_date'] = str(inventory_id.create_date)
            vals2['sc_warehouse_id'] = inventory_id.warehouse_id.id if inventory_id.warehouse_id else 0
            vals2['sc_warehouse'] = inventory_id.warehouse_id.name if inventory_id.warehouse_id else ''
            vals2['exhausted'] = inventory_id.exhausted
            vals2['prefill_counted_quantity'] = dict(inventory_id.fields_get(['prefill_counted_quantity'])['prefill_counted_quantity']['selection'])[inventory_id.prefill_counted_quantity]
            vals2['inventoried_product'] = dict(inventory_id.fields_get(['inventoried_product'])['inventoried_product']['selection'])[inventory_id.inventoried_product]
            location_list = [record.name_get()[0][1] for record in list(set(inventory_id.location_ids))]
            vals2['locations'] = ", ".join(location_list)

            list_data = []
            for record in list(set(inventory_id.location_ids)):
                dict_vals = {}
                dict_vals['id'] = record.id
                dict_vals['name'] = record.name_get()[0][1]
                list_data.append(dict_vals)
            vals2['location_ids'] = list_data
            vals2['company_id'] = inventory_id.company_id.id

            if inventory_id.inventoried_product == 'specific_product':
                product_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_ids))]
                vals2['products'] = ", ".join(product_list)
                pro_list = []
                for rec in inventory_id.product_ids:
                    pro_list.append(rec.id)
                vals2['products_ids'] = str(pro_list)
            else:
                vals2['products'] = ""
                vals2['products_ids'] = "[]"

            if inventory_id.inventoried_product == 'specific_category':
                product_category_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_categories))]
                vals2['product_category'] = ", ".join(product_category_list)
                categ_list = []
                for rec in inventory_id.product_categories:
                    categ_list.append(rec.id)
                vals2['product_category_ids'] = str(categ_list)
            else:
                vals2['product_category'] = ""
                vals2['product_category_ids'] = "[]"
        return vals2

    def app_stock_inventory_data(self):
        vals2 = {}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        vals2['inventory_id'] = self.id
        vals2['inv_ref'] = self.inv_ref
        vals2['name'] = self.name
        vals2['state'] = self.state
        vals2['status'] = dict(self.fields_get(['state'])['state']['selection'])[self.state]
        vals2['color'] = color_dict.get(self.state, '')
        vals2['date_filtered'] = str(self.create_date).split(" ")[0] if self.create_date else ""
        vals2['create_date'] = str(self.create_date)
        vals2['sc_warehouse_id'] = self.warehouse_id.id if self.warehouse_id else 0
        vals2['sc_warehouse'] = self.warehouse_id.name if self.warehouse_id else ''
        vals2['exhausted'] = self.exhausted
        vals2['prefill_counted_quantity'] = dict(self.fields_get(['prefill_counted_quantity'])['prefill_counted_quantity']['selection'])[self.prefill_counted_quantity]
        vals2['inventoried_product'] = dict(self.fields_get(['inventoried_product'])['inventoried_product']['selection'])[self.inventoried_product]
        location_list = [record.name_get()[0][1] for record in list(set(self.location_ids))]
        vals2['locations'] = ", ".join(location_list)

        list_data = []
        for record in list(set(self.location_ids)):
            dict_vals = {}
            dict_vals['id'] = record.id
            dict_vals['name'] = record.name_get()[0][1]
            list_data.append(dict_vals)
        vals2['location_ids'] = list_data
        vals2['company_id'] = self.company_id.id

        if self.inventoried_product == 'specific_product':
            product_list = [record.name_get()[0][1] for record in list(set(self.product_ids))]
            vals2['products'] = ", ".join(product_list)
            pro_list = []
            for rec in self.product_ids:
                pro_list.append(rec.id)
            vals2['products_ids'] = str(pro_list)
        else:
            vals2['products'] = ""
            vals2['products_ids'] = "[]"

        if self.inventoried_product == 'specific_category':
            product_category_list = [record.name_get()[0][1] for record in
                                     list(set(self.product_categories))]
            vals2['product_category'] = ", ".join(product_category_list)
            categ_list = []
            for rec in self.product_categories:
                categ_list.append(rec.id)
            vals2['product_category_ids'] = str(categ_list)
        else:
            vals2['product_category'] = ""
            vals2['product_category_ids'] = "[]"

        data_list = []
        for line in self.line_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['stock_count_id'] = self.id
            vals['product_id'] = line.product_id.id
            vals['pack'] = line.package_id.name if line.package_id else ''
            default_code = line.product_id.default_code or ''
            vals['product'] = '[' + default_code + '] ' + line.product_id.name
            vals['barcode'] = line.temp_barcode or ''
            vals['multi_barcode'] = line.product_id.multi_barcode
            vals['item_no'] = line.product_id.default_code or ''
            vals['tracking'] = line.product_id.tracking
            vals['scanned_qty'] = line.product_qty
            vals['previous_qty'] = line.product_qty
            vals['location_id'] = line.location_id.id
            vals['location'] = line.location_id.name_get()[0][1]
            vals['lot_name'] = line.prod_lot_id.name if line.prod_lot_id else ''
            vals['product_uom_id'] = line.product_uom_id.id
            vals['product_uom'] = line.product_uom_id.name
            vals['category_uom_id'] = line.product_id.uom_id.category_id.id if line.product_id.uom_id.category_id else 0
            vals['uom_id'] = line.uom_id.id if line.uom_id else 0
            vals['uom'] = line.uom_id.name if line.uom_id else ''
            data_list.append(vals)
        vals2['inventory_line_data'] = data_list
        return vals2

    def action_app_confirm(self):
        error_message = 'success'
        try:
            self.action_start()
            # return error_message
            # line_list = []
            # for line in self.env['stock.inventory.line'].read_group(domain=[('inventory_id', '=', self.id)], fields=['product_id', 'location_id', 'package_id'], groupby=['location_id', 'product_id', 'package_id'], lazy=False):
            #     vals = {}
            #     vals['product_id'] = line['product_id'][0] if line['product_id'] else False
            #     vals['location_id'] = line['location_id'][0] if line['location_id'] else False
            #     vals['package_id'] = line['package_id'][0] if line['package_id'] else False
            #     line_list.append((0, 0, vals))
            # self.write({'app_line_ids': line_list})
            # return error_message
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        inventory_data = self.app_stock_inventory_data()
        return {'stock_inventory_data': inventory_data, 'error_message': error_message}

    def action_app_cancel(self):
        error_message = 'success'
        try:
            self.action_cancel_draft()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        inventory_data = self.app_stock_inventory_data()
        return {'stock_inventory_data': inventory_data, 'error_message': error_message}

    def action_app_request_for_approval(self):
        error_message = 'success'
        try:
            self.inv_request_for_approving()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        inventory_data = self.app_stock_inventory_data()
        return {'stock_inventory_data': inventory_data, 'error_message': error_message}

    def action_app_validate(self):
        error_message = 'success'
        try:
            if not self.exists():
                error_message = 'not success'
                inventory_data = self.app_stock_inventory_data()
                return {'error_message': error_message, 'stock_inventory_data': inventory_data}
            self.write({'accounting_date': fields.Date.today()})
            self.action_validate()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        inventory_data = self.app_stock_inventory_data()
        return {'error_message': error_message, 'stock_inventory_data': inventory_data}

    def action_push_data(self, data_list):
        error_message = 'success'
        try:
            for data in data_list:
                if data.get('line_id', False):
                    line_id = self.env['stock.inventory.line'].browse(data['line_id'])
                    if line_id:
                        line_id.write({'product_qty': data.get('qty', 0), 'uom_id': data.get('uom_id', False)})
        except Exception as e:
            error_message = str(tools.ustr(e)).replace('\nNone', '')
            self.env.cr.rollback()
        inventory_data = self.app_stock_inventory_data()
        return {'error_message': error_message, 'stock_inventory_data': inventory_data}
        
    # def action_app_inventory_adjustment(self):
    #     for line in self.app_line_ids:
    #         if line.product_id.tracking == 'none':
    #             inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', False), ('location_id', '=', line.location_id.id), ('inventory_id', '=', self.id)], limit=1)
    #             if inv_line:
    #                 inv_line.write({'product_qty': inv_line.product_qty + line.count_qty})
    #             else:
    #                 line_vals = {}
    #                 line_vals['product_id'] = line.product_id.id
    #                 line_vals['prod_lot_id'] = False
    #                 line_vals['product_qty'] = line.count_qty
    #                 line_vals['location_id'] = line.location_id.id
    #                 line_vals['inventory_id'] = self.id
    #                 self.env['stock.inventory.line'].create(line_vals)
    #         else:
    #             for quant in line.quant_ids:
    #                 inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', quant.lot_id.id if quant.lot_id else False), ('location_id', '=', line.location_id.id), ('inventory_id', '=', self.id)], limit=1)
    #                 if not inv_line:
    #                     line_vals = {}
    #                     line_vals['product_id'] = line.product_id.id
    #                     line_vals['prod_lot_id'] = quant.lot_id.id if quant.lot_id else False
    #                     line_vals['product_qty'] = 0
    #                     line_vals['location_id'] = line.location_id.id
    #                     line_vals['inventory_id'] = self.id
    #                     self.env['stock.inventory.line'].create(line_vals)
    #             for count_quant in line.count_lot_ids:
    #                 inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', count_quant.lot_id.id if count_quant.lot_id else False), ('location_id', '=', line.location_id.id),('inventory_id', '=', self.id)])
    #                 if inv_line:
    #                     inv_line.write({'product_qty': inv_line.product_qty + count_quant.qty})
    #                 else:
    #                     line_vals = {}
    #                     line_vals['product_id'] = line.product_id.id
    #                     line_vals['prod_lot_id'] = count_quant.lot_id.id if count_quant.lot_id else False
    #                     line_vals['product_qty'] = count_quant.qty
    #                     line_vals['location_id'] = line.location_id.id
    #                     line_vals['inventory_id'] = self.id
    #                     self.env['stock.inventory.line'].create(line_vals)

    def action_app_complete(self):
        error_message = 'success'
        try:
            self.action_complete()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        inventory_data = self.app_stock_inventory_data()
        return {'stock_inventory_data': inventory_data, 'error_message': error_message}

    def app_add_inventory_line(self,  line_dict):
        vals = {}
        try:
            product_id = self.env['product.product'].browse(line_dict.get('product_id', False))
            vals['product_id'] = line_dict.get('product_id', False)
            vals['location_id'] = line_dict.get('location_id', False)
            vals['prod_lot_id'] = line_dict.get('prod_lot_id', False)
            vals['package_id'] = line_dict.get('package_id', False)
            vals['product_qty'] = line_dict.get('product_qty', 0)
            vals['product_uom_id'] = product_id.uom_id.id if product_id.uom_id else False
            vals['uom_id'] = line_dict.get('uom_id', False)
            vals['category_uom_id'] = product_id.uom_id.category_id.id
            vals['inventory_id'] = line_dict.get('inventory_id', False)
            line_id = self.env['stock.inventory.line'].create(vals)

            for line in line_id:
                line_vals = {}
                line_vals['line_id'] = line.id
                line_vals['stock_count_id'] = line.inventory_id.id
                line_vals['product_id'] = line.product_id.id
                line_vals['pack'] = line.package_id.name if line.package_id else ''
                default_code = line.product_id.default_code or ''
                line_vals['product'] = '[' + default_code + '] ' + line.product_id.name
                line_vals['barcode'] = line.temp_barcode or ''
                line_vals['multi_barcode'] = line.product_id.multi_barcode
                line_vals['item_no'] = line.product_id.default_code or ''
                line_vals['tracking'] = line.product_id.tracking
                line_vals['scanned_qty'] = line.product_qty
                line_vals['previous_qty'] = line.product_qty
                line_vals['location_id'] = line.location_id.id
                line_vals['location'] = line.location_id.name_get()[0][1]
                line_vals['lot_name'] = line.prod_lot_id.name if line.prod_lot_id else ''
                line_vals['product_uom_id'] = line.product_uom_id.id
                line_vals['product_uom'] = line.product_uom_id.name
                line_vals['category_uom_id'] = line.product_id.uom_id.category_id.id if line.product_id.uom_id.category_id else 0
                line_vals['uom_id'] = line.uom_id.id if line.uom_id else 0
                line_vals['uom'] = line.uom_id.name if line.uom_id else ''
            return {'error_message': 'success', 'line_id': line_id.id, 'inventory_line_data': line_vals}
        except Exception as e:
            self.env.cr.rollback()
            error_message = tools.ustr(e)
            return {'error_message': error_message, 'line_id': 0, 'inventory_line_data': {}}

    def app_delete_stock_lines(self, list_ids):
        error_message = 'success'
        try:
            if len(list_ids) == 1:
                query = "DELETE FROM stock_inventory_line WHERE id = %s" % list_ids[0]
            else:
                query = '''DELETE FROM stock_inventory_line WHERE id in %s''' % (" (%s) " % ','.join(map(str, list_ids)))
            self.env.cr.execute(query)
            return error_message
        except Exception as e:
            self.env.cr.rollback()
            error_message = tools.ustr(e)
            return error_message


StockInventory()


class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT 
                  ru.id AS user_id,
                  COALESCE(ru.stock_count_line_unlink_data, '') AS stock_count_line_unlink_data
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
                old_value = record.get('stock_count_line_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET stock_count_line_unlink_data =%s WHERE id =%s""", (new_value, user_id))
                self._cr.commit()
        return res

    temp_barcode = fields.Char(string="Temp Barcode", compute="_compute_temp_barcode", store=True)

    @api.depends('product_id', 'uom_id')
    def _compute_temp_barcode(self):
        for record in self:
            if record.product_id.multi_barcode:
                barcode_id = self.env['product.template.barcode'].search(
                    [('product_id', '=', record.product_id.id), ('uom_id', '=', record.uom_id.id)], limit=1)
                record.temp_barcode = barcode_id.name if barcode_id.name else ''
            else:
                record.temp_barcode = record.product_id.barcode or ''


InventoryLine()

# class StockInventoryLineApp(models.Model):
#     _name = 'stock.inventory.line.app'
#     _description = 'Stock Inventory Line App'
#
#     inventory_id = fields.Many2one('stock.inventory', string='Stock Count')
#     state = fields.Selection(related='inventory_id.state', copy=False, store=True, string='Status')
#     location_id = fields.Many2one('stock.location', string='Location')
#     product_id = fields.Many2one('product.product', required=True, string='Product')
#     package_id = fields.Many2one(
#         'stock.quant.package', 'Pack', index=True, check_company=True,
#         domain="[('location_id', '=', location_id)]",
#     )
#     existing_qty = fields.Float(compute='compute_existing_qty', store=False, string='Existing Qty')
#     quant_ids = fields.Many2many('stock.quant', compute='_get_stock_quant', string='Quants')
#     count_qty = fields.Float(string='Count Quantity')
#     count_lot_ids = fields.One2many('stock.inventory.quant', 'count_line_id', string='Lot/Serial Nos')
#     tracking = fields.Selection(related='product_id.tracking', string='Tracking')
#
#     @api.depends('quant_ids', 'state', 'quant_ids.quantity', 'quant_ids.lot_id')
#     def compute_existing_qty(self):
#         for record in self:
#             record.existing_qty = sum([x.quantity for x in record.quant_ids])
#
#     @api.depends('product_id', 'state')
#     def _get_stock_quant(self):
#         for record in self:
#             if record.product_id:
#                 quant_ids = self.env['stock.quant'].search([('product_id', '=', record.product_id.id), ('location_id', '=', record.location_id.id), ('package_id', '=', record.package_id.id if record.package_id else False)]).ids
#             else:
#                 quant_ids = []
#             record.quant_ids = [(6, 0, quant_ids)]
#
#     @api.constrains('product_id', 'inventory_id', 'location_id', 'package_id')
#     def _check_product(self):
#         for record in self:
#             ids = self.env['stock.inventory.line.app'].search([('product_id', '=', record.product_id.id), ('inventory_id', '=', record.inventory_id.id), ('location_id', '=', record.location_id.id), ('package_id', '=', record.package_id.id if record.package_id else False)])
#             if len(ids) > 1:
#                 raise ValidationError('Duplicate Products is not allowed.')
#
#     def find_lot_number(self, lot_name):
#         self.ensure_one()
#         lot_id = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('name', '=', lot_name)], limit=1)
#         if lot_id:
#             vals = {}
#             vals['lot_name'] = lot_id.name
#             return vals
#         else:
#             return {}
#
#     def action_recount(self):
#         for record in self:
#             record.count_qty = 0
#             record.count_lot_ids.unlink()
#
#     def view_existing_data(self):
#         return {
#             'name': 'Lot/Serial Numbers',
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form'),
#             'res_model': 'stock.inventory.line.app',
#             'target': 'new',
#             'res_id': self.ids[0],
#         }
#
#     def view_count_data(self):
#         if self.tracking == 'none':
#             view_id = self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form3')
#         else:
#             view_id = self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form2')
#         return {
#             'name': 'Lot/Serial Numbers',
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': view_id,
#             'res_model': 'stock.inventory.line.app',
#             'target': 'new',
#             'res_id': self.ids[0],
#         }
#
#     def save(self):
#         return {'type': 'ir.actions.act_window_close'}
#
#     def action_cancel(self):
#         for record in self:
#             record.write({'state': 'cancel'})
#             if all(x.state == 'cancel' for x in record.inventory_id.line_ids):
#                 record.inventory_id.action_cancel()
#
# StockInventoryLineApp()
#
#
# class StockInventoryQuant(models.Model):
#     _name = 'stock.inventory.quant'
#     _description = 'Stock Count Quant'
#     _rec_name = 'product_id'
#     _order = 'id desc'
#
#     count_line_id = fields.Many2one('stock.inventory.line.app', string='Count Line')
#     product_id = fields.Many2one('product.product', required=True, string='Product')
#     lot_id = fields.Many2one('stock.production.lot', required=False, string='Lot/Serial No')
#     qty = fields.Float()
#
#
# StockInventoryQuant()