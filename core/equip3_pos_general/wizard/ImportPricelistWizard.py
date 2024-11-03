# -*- coding: utf-8 -*-

import tempfile
import binascii
import xlrd

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ImportPricelistWizard(models.TransientModel):
    _name = 'import.pricelist.wizard'

    name = fields.Char(string="PriceList Name")
    file = fields.Binary('Add File', attachment=False)
    file_name = fields.Char('File Name')

    def import_pricelist_records(self):
        pricelist_obj = self.env['product.pricelist'].search([('name', '=', self.name)],limit=1)
        if not pricelist_obj:
            pricelist_obj = self.env['product.pricelist'].create({'name':self.name})
        pricelist_id = False
        if pricelist_obj:
            pricelist_id = pricelist_obj.id

        # Product Map
        product_data = self.env['product.template'].search_read([], ['name'])
        product_dict = dict([(p.get('name'), p.get('id')) for p in product_data])
        if '.xlsx' in self.file_name and pricelist_id:
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            keys = sheet.row_values(0)
            xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]
            for row in xls_reader:
                line = dict(zip(keys, row))
                date_from , date_to = '' ,''
                if line.get('date_start'):
                    date_from = xlrd.xldate.xldate_as_datetime(line.get('date_start'), workbook.datemode)
                if line.get('date_end'):
                    date_to = xlrd.xldate.xldate_as_datetime(line.get('date_end'), workbook.datemode)
                if line.get('applied_on') == '2_product_category':
                    if line.get('external_id'):
                        module, name = line.get('external_id').split('.', 1)
                        self.env.cr.execute(
                            "SELECT res_id FROM ir_model_data WHERE name='%s'" % (name))
                        categ_ids = self.env.cr.fetchall()
                        if categ_ids:
                            vals = {}
                            vals['pricelist_id'] = pricelist_id
                            vals['applied_on'] = '2_product_category'
                            vals['categ_id'] = categ_ids[0]
                            if date_from:
                                vals['date_start'] = date_from
                            if date_to:
                                vals['date_end'] = date_to
                            vals['minimum_price'] = line.get('minimum_price')
                            vals['maximum_price'] = line.get('maximum_price')
                            if line.get('pricelist_uom_id'):
                                uom_obj = self.env['uom.uom'].search(
                                    [('name', '=', line.get('pricelist_uom_id'))], limit=1)
                                vals['pricelist_uom_id'] = uom_obj.id
                            if line.get('compute_price')=='fixed':
                                vals['compute_price'] = 'fixed'
                                vals['fixed_price'] = line.get('fixed_price')
                            elif line.get('compute_price')=='percentage':
                                vals['compute_price'] = 'percentage'
                                vals['percent_price'] = line.get('percent_price')
                            elif line.get('compute_price') == 'formula':
                                vals['compute_price'] = 'formula'
                                vals['price_discount'] = line.get('percent_price')
                                vals['price_surcharge'] = line.get('price_surcharge')
                                vals['price_round'] = line.get('price_round')
                                vals['price_min_margin'] = line.get('price_min_margin')
                                vals['price_max_margin'] = line.get('price_max_margin')
                            vals['min_quantity'] = line.get('min_qty')
                            self.env['product.pricelist.item'].create(vals)
                elif line.get('applied_on') == '0_product_variant':
                    module, name = line.get('external_id').split('.', 1)
                    self.env.cr.execute(
                        "SELECT res_id FROM ir_model_data WHERE name='%s'" % (name))
                    product_ids = self.env.cr.fetchall()
                    if product_ids:
                        product_obj = self.env['product.product'].browse(product_ids[0])
                        if not product_obj:
                            raise ValidationError(str(line.get('product_name'))+str(" variant not available in the system."))
                        else:
                            product_created = self.env['product.pricelist.item'].search([
                                ('pricelist_id','=',pricelist_id),
                                ('product_id','=',product_obj.id),
                                ('min_quantity','=',line.get('min_qty')),])
                            if product_created:
                                continue
                            else:
                                vals = {}
                                vals['product_id'] = product_obj.id
                                vals['pricelist_id'] = pricelist_id
                                vals['applied_on'] = '0_product_variant'
                                if date_from:
                                    vals['date_start'] = date_from
                                if date_to:
                                    vals['date_end'] = date_to
                                vals['minimum_price'] = line.get('minimum_price')
                                vals['maximum_price'] = line.get('maximum_price')
                                vals['uom_id'] = product_obj.uom_id.id if product_obj.uom_id else False
                                if line.get('pricelist_uom_id'):
                                    uom_obj = self.env['uom.uom'].search(
                                        [('name', '=', line.get('pricelist_uom_id'))], limit=1)
                                    vals['pricelist_uom_id'] = uom_obj.id
                                if line.get('compute_price')=='fixed':
                                    vals['compute_price'] = 'fixed'
                                    vals['fixed_price'] = line.get('fixed_price')
                                elif line.get('compute_price')=='percentage':
                                    vals['compute_price'] = 'percentage'
                                    vals['percent_price'] = line.get('percent_price')
                                elif line.get('compute_price')=='formula':
                                    vals['compute_price'] = 'formula'
                                    vals['price_discount'] = line.get('percent_price')
                                    vals['price_surcharge'] = line.get('price_surcharge')
                                    vals['price_round'] = line.get('price_round')
                                    vals['price_min_margin'] = line.get('price_min_margin')
                                    vals['price_max_margin'] = line.get('price_max_margin')
                                vals['min_quantity'] = line.get('min_qty')
                                self.env['product.pricelist.item'].create(vals)
                elif line.get('applied_on') == '1_product':
                    module, name = line.get('external_id').split('.', 1)
                    self.env.cr.execute(
                        "SELECT res_id FROM ir_model_data WHERE name='%s'" % (name))
                    product_ids = self.env.cr.fetchall()
                    if product_ids:
                        product_obj = self.env['product.template'].browse(product_ids[0])
                        if not product_obj:
                            raise ValidationError(str(line.get('external_id'))+str(" template not available in the system."))
                        else:
                            product_created = self.env['product.pricelist.item'].search([
                                ('pricelist_id','=',pricelist_id),
                                ('product_tmpl_id','=',product_obj.id),
                                ('min_quantity','=',line.get('min_qty')),])
                            if product_created:
                                continue
                            else:
                                vals = {}
                                vals['product_tmpl_id'] = product_obj.id
                                vals['pricelist_id'] = pricelist_id
                                vals['applied_on'] = '1_product'
                                if date_from:
                                    vals['date_start'] = date_from
                                if date_to:
                                    vals['date_end'] = date_to
                                vals['minimum_price'] = line.get('minimum_price')
                                vals['maximum_price'] = line.get('maximum_price')
                                vals['uom_id'] = product_obj.uom_id.id if product_obj.uom_id else False
                                if line.get('pricelist_uom_id'):
                                    uom_obj = self.env['uom.uom'].search(
                                        [('name', '=', line.get('pricelist_uom_id'))], limit=1)
                                    vals['pricelist_uom_id'] = uom_obj.id
                                if line.get('compute_price')=='fixed':
                                    vals['compute_price'] = 'fixed'
                                    vals['fixed_price'] = line.get('fixed_price')
                                elif line.get('compute_price')=='percentage':
                                    vals['compute_price'] = 'percentage'
                                    vals['percent_price'] = line.get('percent_price')
                                elif line.get('compute_price')=='formula':
                                    vals['compute_price'] = 'formula'
                                    vals['price_discount'] = line.get('percent_price')
                                    vals['price_surcharge'] = line.get('price_surcharge')
                                    vals['price_round'] = line.get('price_round')
                                    vals['price_min_margin'] = line.get('price_min_margin')
                                    vals['price_max_margin'] = line.get('price_max_margin')
                                vals['min_quantity'] = line.get('min_qty')
                                self.env['product.pricelist.item'].create(vals)
                elif line.get('applied_on') == '4_pos_category':
                    module, name = line.get('external_id').split('.', 1)
                    self.env.cr.execute(
                        "SELECT res_id FROM ir_model_data WHERE module='%s' AND name='%s'" % (module, name))
                    product_id = self.env.cr.fetchall()
                    product_obj = self.env['pos.category'].browse(product_id)
                    if not product_obj:
                        raise ValidationError(str(line.get('external_id'))+str(" template not available in the system."))
                    else:
                        product_created = self.env['product.pricelist.item'].search([
                            ('pricelist_id','=',pricelist_id),
                            ('pos_category_id','=',product_obj.id),
                            ('min_quantity','=',line.get('min_qty')),])
                        if product_created:
                            continue
                        else:
                            vals = {}
                            vals['pos_category_id'] = product_obj.id
                            vals['pricelist_id'] = pricelist_id
                            vals['applied_on'] = '4_pos_category'
                            if date_from:
                                vals['date_start'] = date_from
                            if date_to:
                                vals['date_end'] = date_to
                            vals['minimum_price'] = line.get('minimum_price')
                            vals['maximum_price'] = line.get('maximum_price')
                            if line.get('pricelist_uom_id'):
                                uom_obj = self.env['uom.uom'].search(
                                    [('name', '=', line.get('pricelist_uom_id'))], limit=1)
                                vals['pricelist_uom_id'] = uom_obj.id
                            if line.get('compute_price')=='fixed':
                                vals['compute_price'] = 'fixed'
                                vals['fixed_price'] = line.get('fixed_price')
                            elif line.get('compute_price')=='percentage':
                                vals['compute_price'] = 'percentage'
                                vals['percent_price'] = line.get('percent_price')
                            elif line.get('compute_price')=='formula':
                                vals['compute_price'] = 'formula'
                                vals['price_discount'] = line.get('percent_price')
                                vals['price_surcharge'] = line.get('price_surcharge')
                                vals['price_round'] = line.get('price_round')
                                vals['price_min_margin'] = line.get('price_min_margin')
                                vals['price_max_margin'] = line.get('price_max_margin')
                            vals['min_quantity'] = line.get('min_qty')
                            self.env['product.pricelist.item'].create(vals)
        return True