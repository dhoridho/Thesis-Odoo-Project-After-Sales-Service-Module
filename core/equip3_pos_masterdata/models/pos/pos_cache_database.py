# -*- coding: utf-8 -*-
import json
import ast
import logging
from datetime import datetime, timedelta
from odoo import api, models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

def str_to_date(date):
    return datetime.strptime(date,'%Y-%m-%d %H:%M:%S')

class PosCacheDatabase(models.Model):
    _name = "pos.cache.database"
    _description = "Management POS database"
    _rec_name = "res_id"
    _order = 'res_model'

    res_id = fields.Char('Id')
    res_model = fields.Char('Model')
    deleted = fields.Boolean('Deleted', default=0)

    def auto_reinstall_pos_call_log_cron(self):
        _logger.info('[auto_reinstall_pos_call_log_cron] Start - Installing Model')

        self.api_reinstall_pos_call_log('product.product')
        self.api_reinstall_pos_call_log('product.template')
        self.api_reinstall_pos_call_log('product.template.barcode')
        self.api_reinstall_pos_call_log('product.pricelist.item')
        self.api_reinstall_pos_call_log('res.partner')
        self.api_reinstall_pos_call_log('stock.production.lot')
        self.api_reinstall_pos_call_log('stock.quant')
        self.api_reinstall_pos_call_log('product.brand')
        self.api_reinstall_pos_call_log('pos.voucher')

        # Start Promotions
        self.api_reinstall_pos_call_log('pos.promotion')
        self.api_reinstall_pos_call_log('pos.promotion.discount.order')
        self.api_reinstall_pos_call_log('pos.promotion.discount.category')
        self.api_reinstall_pos_call_log('pos.promotion.discount.quantity')
        self.api_reinstall_pos_call_log('pos.promotion.gift.condition')
        self.api_reinstall_pos_call_log('pos.promotion.gift.free')
        self.api_reinstall_pos_call_log('pos.promotion.discount.condition')
        self.api_reinstall_pos_call_log('pos.promotion.discount.apply')
        self.api_reinstall_pos_call_log('pos.promotion.special.category')
        self.api_reinstall_pos_call_log('pos.promotion.selected.brand')
        self.api_reinstall_pos_call_log('pos.promotion.tebus.murah.selected.brand')
        self.api_reinstall_pos_call_log('pos.promotion.specific.product')
        self.api_reinstall_pos_call_log('pos.promotion.tebus.murah')
        self.api_reinstall_pos_call_log('pos.promotion.multi.buy')
        self.api_reinstall_pos_call_log('pos.promotion.multilevel.condition')
        self.api_reinstall_pos_call_log('pos.promotion.multilevel.gift')
        self.api_reinstall_pos_call_log('pos.promotion.price')
        # End Promotions
        
        self.api_reinstall_pos_call_log('pos.order')
        self.api_reinstall_pos_call_log('pos.order.line')

        self.api_reinstall_pos_call_log('account.move') 
        self.api_reinstall_pos_call_log('account.move.line') 

        _logger.info('[auto_reinstall_pos_call_log_cron] Finish - Installing Model')

        return False

    def api_reinstall_pos_call_log(self, model_name):
        max_load = 9999;
        next_load = 10000;
        first_load = 10000;

        model_max_id = self.get_model_max_id(model_name)
        _logger.info('[api_reinstall_pos_call_log] model_max_id: %s' % str(model_max_id))

        def installing_data(model_name, min_id, max_id):
            if min_id == 0:
                max_id = max_load;

            result_count = self.install_data_from_backend(model_name, min_id=min_id, max_id=max_id)
            _logger.info(f'[api_reinstall_pos_call_log] model: {model_name} result_count {result_count}')

            min_id += next_load;
            if result_count > 0:
                max_id += next_load;
                installing_data(model_name, min_id, max_id)
            else:
                if max_id < model_max_id:
                    max_id += next_load;
                    installing_data(model_name, min_id, max_id)

        installing_data(model_name, min_id=0, max_id=first_load)
        return False


    def request_pos_sessions_online_reload_by_channel(self, channel):
        sessions = self.env['pos.session'].sudo().search([
            ('state', '=', 'opened')
        ])
        for session in sessions:
            self.env['bus.bus'].sendmany(
                [[(self.env.cr.dbname, channel, session.user_id.id), {}]])
        return True

    def get_modifiers_backend(self, write_date, model_name, config_id=None):
        config = config_id and self.env['pos.config'].sudo().browse(config_id) or False
        field_list = self.sudo().get_fields_by_model(model_name)
        results = []
        domain = []
        if write_date:
            to_date = datetime.strptime(write_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(seconds=1)
            to_date = to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            domain += [('write_date', '>', to_date)]

        if model_name == 'product.product':
            domain += [('product_tmpl_id.available_in_pos', '=', True)]
        if model_name == 'product.template':
            domain += [('available_in_pos', '=', True)]
        if model_name == 'stock.quant':
            domain += [('product_tmpl_id.available_in_pos', '=', True),('product_tmpl_id.sale_ok', '=', True),('location_id.usage','=','internal')]
        if model_name == 'pos.order.line':
            domain += [('order_id', '!=', False)]
        if model_name == 'res.partner':
            domain += self._sync_pos_partner_domain()
        if model_name == 'product.pricelist.item':
            if config and config.pricelist_id:
                domain=[('pricelist_id','=',config.pricelist_id.id)]
                
        records = self.env[model_name].sudo().search_read(domain, field_list)
        return records


    def get_count_modifiers_backend_all_models(self, model_values, config_id=None):
        count = 0
        for res_model, write_date in model_values.items():
            to_date = datetime.strptime(write_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(
                seconds=1)
            if res_model not in ['product.product', 'product.template']:
                to_date = to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                count += self.sudo().search_count([('write_date', '>', to_date), ('res_model', '=', res_model)])
            else:
                product_template_ids = [p.id for p in self.env['product.template'].search([('write_date', '>', to_date)])]
                count += self.env[res_model].sudo().search_count(['|', ('write_date', '>', to_date), ('product_tmpl_id', 'in', product_template_ids)])
        return count


    def onLoadPosSyncPricelistItems(self, model_values, config_id=None):
        results = {}
        for model, write_date in model_values.items():
            values = self.sudo().get_modifiers_backend(write_date, model, config_id)
            results[model] = values

        if not model_values:
            model = 'product.pricelist.item'
            values = self.sudo().get_modifiers_backend(False, model, config_id)
            results[model] = values

        return results

    def onLoadPosSyncProducts(self, model_values, config_id=None):
        results = {}
        for model, write_date in model_values.items():
            values = self.sudo().get_modifiers_backend(write_date, model, config_id)
            results[model] = values
        return results

    def onLoadPosSyncPartners(self, model_values, config_id=None):
        results = {}
        for model, write_date in model_values.items():
            values = self.sudo().get_modifiers_backend(write_date, model, config_id)
            results[model] = values
        return results

    def syncProductsPartners(self, model_values, config_id=None):
        results = {}
        for model, write_date in model_values.items():
            values = self.sudo().get_modifiers_backend(write_date, model, config_id)
            results[model] = values
        return results
    
    def onLoadPosSyncPromotions(self, model_values, config_id=None):
        results = {}
        promotion_ids = []
        write_date = False
        if model_values.get('pos.promotion'):
            write_date = datetime.strptime(model_values['pos.promotion'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999')
        config = self.env['pos.config'].sudo().browse(config_id)

        for model in self._pos_promotion_models:
            field_list = self.sudo().get_fields_by_model(model)
            domain = []
            if model == 'pos.promotion':
                if write_date:
                    domain += [('write_date','>', write_date)]
                domain += [ 
                    ('active','=',True),
                    ('state', '=', 'active'),
                    ('end_date','>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
                    ('id', 'in', config.promotion_ids.ids)
                ]
            else:
              domain = [['promotion_id', 'in', promotion_ids]] 

            records = self.env[model].sudo().search_read(domain, field_list)
            if model == 'pos.promotion':
                promotion_ids = [r['id'] for r in records]

            results[model] = records
        return results

    def onLoadForceSyncPromotions(self, config_id=None):
        results = {}
        promotion_ids = []
        config = self.env['pos.config'].sudo().browse(config_id)

        for model in self._pos_promotion_models:
            field_list = self.sudo().get_fields_by_model(model)
            domain = []
            if model == 'pos.promotion':
                domain += [ 
                    ('active','=',True),
                    ('state', '=', 'active'),
                    ('end_date','>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
                    ('id', 'in', config.promotion_ids.ids)
                ]
            else:
                domain = [['promotion_id', 'in', promotion_ids]] 

            records = self.env[model].sudo().search_read(domain, field_list)
            if model == 'pos.promotion':
                promotion_ids = [r['id'] for r in records]

            results[model] = records
        return results
        

    def get_fields_by_model(self, model_name):
        params = self.env['ir.config_parameter'].sudo().get_param(model_name)
        if not params:
            list_fields = self.env[model_name].sudo().fields_get()
            fields_load = []
            for k, v in list_fields.items():
                if v['type'] not in ['binary']:
                    fields_load.append(k)
            return fields_load
        else:
            params = ast.literal_eval(params)
            return params.get('fields', [])

    def get_domain_by_model(self, model_name):
        params = self.env['ir.config_parameter'].sudo().get_param(model_name)
        if not params:
            return []
        else:
            params = ast.literal_eval(params)
            return params.get('domain', [])

    def install_data_from_backend(self, model_name=None, min_id=0, max_id=1999):
        _logger.info('[install_data_from_backend] model %s from id %s to id %s' % (model_name, min_id, max_id))
        datas = self.installing_datas(model_name, min_id, max_id)
        return len(datas)

    def get_model_max_id(self, model_name):
        max_id = 0
        domain = [('active', '=', True)]

        if model_name == 'product.product':
            domain += [('product_tmpl_id.available_in_pos', '=', True)]
        if model_name == 'product.template':
            domain += [('available_in_pos', '=', True)]

        if model_name in ['account.move', 'account.move.line']:
            domain = []

        result = self.env[model_name].sudo().search_read(domain, ['id'], order='id desc', limit=1)
        if result:
            max_id = result[0]['id']
        return max_id
        
    def install_data(self, model_name=None, min_id=0, max_id=1999,config_id=False):
        _logger.info('[install_data] model %s from id %s to id %s' % (model_name, min_id, max_id))
        self.env.cr.execute("SELECT id, call_results FROM pos_call_log WHERE active=true AND min_id=%s AND max_id=%s AND call_model='%s' AND (company_id = %s OR company_id IS NULL)" % (min_id, max_id, model_name, self.env.company.id))        
        old_logs = self.env.cr.fetchall()
        pos_config = self.env['pos.config'].browse(config_id)
        if len(old_logs) == 0:
            datas = self.installing_datas(model_name, min_id, max_id)
        else:
            datas = old_logs[0][1]

        if model_name == 'account.move':
            datas = self._filter_install_data_account_move(datas, pos_config)
        if model_name == 'account.move.line':
            datas = self._filter_install_data_account_move_line(datas, pos_config)

        if model_name == 'pos.order':
            datas = self._filter_install_data_pos_order(datas, pos_config)
        if model_name == 'pos.order.line':
            datas = self._filter_install_data_pos_order_line(datas, pos_config)

        return datas

    def _filter_install_data_pos_order(self, datas, pos_config):
        today = datetime.today()
        date_filter = False
        _type = pos_config.filter_load_pos_order
        if _type == 'today':
            date_filter = datetime.strptime(datetime.now().strftime('%Y-%m-%d 00:00:00'),'%Y-%m-%d %H:%M:%S')
        if _type == 'last_3_days':
            date_filter = today + timedelta(days=-3)
        if _type == 'last_7_days':
            date_filter = today + timedelta(days=-7)
        if _type == 'last_1_month':
            date_filter = today + timedelta(days=-30)
        if _type == 'last_1_year':
            date_filter = today + timedelta(days=-365)

        if date_filter and datas and datas != '[]':
            datas = json.loads(datas)
            if pos_config.pos_orders_load_orders_another_pos:
                datas = list(filter(lambda o: str_to_date(o['write_date'][:19]) >= date_filter and o['config_id'][0] == pos_config.id, datas))
            else:
                datas = list(filter(lambda o: str_to_date(o['write_date'][:19]) >= date_filter, datas))
            datas = json.dumps(datas)
        return datas

    def _filter_install_data_pos_order_line(self, datas, pos_config):
        today = datetime.today()
        date_filter = False
        _type = pos_config.filter_load_pos_order
        if _type == 'today':
            date_filter = datetime.strptime(datetime.now().strftime('%Y-%m-%d 00:00:00'),'%Y-%m-%d %H:%M:%S')
        if _type == 'last_3_days':
            date_filter = today + timedelta(days=-3)
        if _type == 'last_7_days':
            date_filter = today + timedelta(days=-7)
        if _type == 'last_1_month':
            date_filter = today + timedelta(days=-30)
        if _type == 'last_1_year':
            date_filter = today + timedelta(days=-365)

        if date_filter and datas and datas != '[]':
            datas = json.loads(datas)
            if pos_config.pos_orders_load_orders_another_pos:
                datas = list(filter(lambda o: str_to_date(o['write_date'][:19]) >= date_filter and o['config_id'][0] == pos_config.id, datas))
            else:
                datas = list(filter(lambda o: str_to_date(o['write_date'][:19]) >= date_filter, datas))
            datas = json.dumps(datas)
        return datas

    def _filter_install_data_account_move(self, datas, pos_config):
        today = datetime.today()
        date_filter = False
        _type = pos_config.load_invoices_type
        if _type == 'today':
            date_filter = datetime.strptime(datetime.now().strftime('%Y-%m-%d 00:00:00'),'%Y-%m-%d %H:%M:%S')
        if _type == 'last_3_days':
            date_filter = today + timedelta(days=-3)
        if _type == 'last_7_days':
            date_filter = today + timedelta(days=-7)
        if _type == 'last_1_month':
            date_filter = today + timedelta(days=-30)
        if _type == 'last_1_year':
            date_filter = today + timedelta(days=-365)

        if date_filter and datas and datas != '[]':
            datas = json.loads(datas)
            datas = list(filter(lambda o: str_to_date(o['write_date'][:19]) >= date_filter, datas))
            datas = json.dumps(datas)
        return datas

    def _filter_install_data_account_move_line(self, datas, pos_config):
        today = datetime.today()
        date_filter = False
        _type = pos_config.load_invoices_type
        if _type == 'today':
            date_filter = datetime.strptime(datetime.now().strftime('%Y-%m-%d 00:00:00'),'%Y-%m-%d %H:%M:%S')
        if _type == 'last_3_days':
            date_filter = today + timedelta(days=-3)
        if _type == 'last_7_days':
            date_filter = today + timedelta(days=-7)
        if _type == 'last_1_month':
            date_filter = today + timedelta(days=-30)
        if _type == 'last_1_year':
            date_filter = today + timedelta(days=-365)

        if date_filter and datas and datas != '[]':
            datas = json.loads(datas)
            datas = list(filter(lambda o: str_to_date(o['write_date'][:19]) >= date_filter, datas))
            datas = json.dumps(datas)
        return datas


    _pos_promotion_models = [
        'pos.promotion', 'pos.promotion.discount.order', 'pos.promotion.discount.category',
        'pos.promotion.discount.quantity', 'pos.promotion.gift.condition', 'pos.promotion.gift.free', 
        'pos.promotion.discount.condition', 'pos.promotion.discount.apply', 'pos.promotion.special.category', 'pos.promotion.selected.brand', 'pos.promotion.tebus.murah.selected.brand', 
        'pos.promotion.multi.buy', 'pos.promotion.price','pos.promotion.specific.product', 'pos.promotion.tebus.murah',
        'pos.promotion.multilevel.condition', 'pos.promotion.multilevel.gift'
    ]

    def installing_datas(self, model_name, min_id, max_id):
        cache_obj = self.sudo()
        log_obj = self.env['pos.call.log'].sudo()
        domain = [('id', '>=', min_id), ('id', '<=', max_id)]

        if model_name == 'product.pricelist.item':
            domain.append(('company_id', 'in', [self.env.company.id,False]))
        elif model_name == 'pos.voucher':
            domain += [['end_date','>', datetime.now().strftime('%Y-%m-%d 00:00:00')], ['state','=', 'active']]
        elif model_name in self._pos_promotion_models:
            domain += [('active','=',True)]
        elif model_name == 'product.template.barcode':
            domain+= [('product_id.available_in_pos', '=', True)]
        elif model_name in ['product.template','product.product']:
            domain+=[['company_id','in',[self.env.company.id,False]]]
        elif model_name in ['product.brand']:
            domain+=[('active','=',True)]
        else:
            domain.append(('company_id', '=', self.env.company.id))

        if model_name in ['product.product', 'product.template']:
            domain += self.env['product.product'].pos_product_domain()
            domain.append(('sale_ok', '=', True))
            domain.append(('type', 'in', ('service','product')))
            domain.append(('active', '=', True))
        if model_name == 'stock.production.lot':
            domain += ['|', ('expiration_date','>=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), ('expiration_date','=', False)]
        if model_name == 'stock.quant':
            domain+= [('product_tmpl_id.available_in_pos', '=', True),('product_tmpl_id.sale_ok', '=', True),('location_id.usage','=','internal')]

        if 'pos.promotion' in model_name:
            if model_name == 'pos.promotion':
                domain += [('end_date','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S')),('state','=','active')]
            else:
                domain += [('promotion_id.end_date','>=',datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            ('promotion_id.state','=','active')]
                            
        if 'res.partner' in model_name:
            domain += self._sync_pos_partner_domain()

        field_list = cache_obj.get_fields_by_model(model_name)
        _logger.info('[installing_datas] for model : %s with fields: %s' % (model_name, field_list))
        datas = self.env[model_name].sudo().search_read(domain, field_list)
        datas = log_obj.covert_datetime(model_name, datas)
        call_results = json.dumps(datas)
        call_fields = json.dumps(field_list)
        vals = {
            'active': True,
            'min_id': min_id,
            'max_id': max_id,
            'call_fields': call_fields,
            'call_results': call_results,
            'call_model': model_name,
            'call_domain': json.dumps(domain),
            'company_id': self.env.company.id,
        }
        logs = log_obj.search([
            ('min_id', '=', min_id),
            ('max_id', '=', max_id),
            ('call_model', '=', model_name),
            ('company_id', '=', self.env.company.id),
        ])
        logs = log_obj.search([
            ('min_id', '=', min_id),
            ('max_id', '=', max_id),
            ('call_model', '=', model_name),
        ])
        if logs:
            logs.write(vals)
        else:
            log_obj.create(vals)
        self.env.cr.commit()
        _logger.info('DONE installing_datas')
        return datas

    def insert_data(self, model, record_id):
        if type(model) == list:
            return False
        last_caches = self.search([('res_id', '=', str(record_id)), ('res_model', '=', model)], limit=1)
        if last_caches:
            last_caches.write({
                'res_model': model,
                'deleted': False
            })
        else:
            self.create({
                'res_id': str(record_id),
                'res_model': model,
                'deleted': False
            })
        return True

    def get_data(self, model, record_id):
        data = {
            'model': model
        }
        fields_read_load = self.sudo().get_fields_by_model(model)
        if model in ['res.partner', 'product.product', 'product.template']:
            fields_read_load.append('active')
        if model in ['product.product', 'product.template']:
            fields_read_load.append('sale_ok')
        vals = self.env[model].sudo().search_read([('id', '=', record_id)], fields_read_load)
        if vals:
            data.update(vals[0])
            return data
        else:
            return None

    def remove_record(self, model, record_id):
        records = self.sudo().search([('res_id', '=', str(record_id)), ('res_model', '=', model)])
        if records:
            records.write({
                'deleted': True,
            })
        else:
            vals = {
                'res_id': str(record_id),
                'res_model': model,
                'deleted': True,
            }
            self.create(vals)
        return True

    def save_parameter_models_load(self, model_datas):
        for model_name, value in model_datas.items():
            self.env['ir.config_parameter'].sudo().set_param(model_name, value)
        return True

    def save_pos_screen_parameter_models_and_fields_load(self, vals):
        self.env['ir.config_parameter'].sudo().set_param('pos_screen_parameter_models_and_fields_load', json.dumps(vals))
        return True

    def get_childs_of_pricelist(self, pricelist_id):
        res_ids = []
        self.env.cr.execute("""
            SELECT 1, ARRAY_AGG(id) FROM product_pricelist_item
            WHERE pricelist_id = %s
            GROUP BY 1
        """ % str(int(pricelist_id)))
        results = self.env.cr.fetchall()
        for result in results:
            res_ids = result[1]
        return res_ids

    def get_existing_ids_of_promotion_and_childs(self, config):
        models = {}

        end_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        promotion_ids = config.promotion_ids.ids
        if promotion_ids:
            for model in self._pos_promotion_models:
                models[model] = []
                model_name = str(model).replace('.','_')

                if model == 'pos.promotion':
                    query = """
                        SELECT 1, ARRAY_AGG(id) FROM pos_promotion 
                        WHERE state = 'active'
                            AND end_date >= '{end_date}'
                            AND id IN ({promotion_ids})
                        GROUP BY 1
                    """.format(end_date=end_date, promotion_ids=str(promotion_ids)[1:-1])
                    self.env.cr.execute(query)
                    results = self.env.cr.fetchall()
                    for result in results:
                        models[model] = result[1]

                if model != 'pos.promotion':
                    query = """
                        SELECT 1, ARRAY_AGG(c.id) FROM {model_name} AS c
                        INNER JOIN pos_promotion AS p ON p.id = c.promotion_id
                        WHERE p.state = 'active'
                            AND p.end_date >= '{end_date}'
                            AND p.id IN ({promotion_ids})
                        GROUP BY 1
                    """.format(model_name=model_name, end_date=end_date, promotion_ids=str(promotion_ids)[1:-1])
                    self.env.cr.execute(query)
                    results = self.env.cr.fetchall()
                    for result in results:
                        models[model] = result[1]

        return models

    def _product_product_fields(self):
        return [
            'name', 'display_name', 'lst_price', 'standard_price', 'categ_id', 'taxes_id', 'barcode', 'default_code',  
            'product_tmpl_id', 'tracking', 'write_date', 'available_in_pos', 'attribute_line_ids', 'type', 'active', 
            'product_brand_ids', 'multi_uom', 'supplier_barcode', 'uom_po_id', 'barcode_line_ids', 'uom_id', 'sale_ok',
            'supplier_taxes_id', 'volume', 'weight',  'pos_sequence', 'qty_warning_out_stock', 'is_gift_product', 'sh_qr_code',
            'company_id', 'uom_ids', 'plu_number',
        ]

    def _product_template_fields(self):
        return [
            'name', 'display_name', 'categ_id', 'lst_price', 'product_variant_id', 'product_variant_ids', 'product_variant_count', 
            'taxes_id','barcode', 'standard_price', 'uom_id', 'default_code', 'sh_qr_code', 'product_brand_ids', 'active', 'write_date',
        ]

    def _res_partner_fields(self):
        return [
            'name', 'street', 'city', 'state_id', 'country_id', 'vat', 'lang', 'phone', 'zip', 'mobile', 
            'email', 'barcode', 'write_date', 'property_account_position_id', 'display_name', 'special_name', 
            'ref', 'discount_id', 'property_product_pricelist', 'birthday_date', 'group_ids', 
            'company_id', 'active', 'pos_loyalty_point', 'pos_loyalty_type', 'is_pos_member', 'pos_branch_id'
        ]

    def _sync_pos_product_template_domain(self, vals):
        return [('available_in_pos','=', True)]


    def _sync_pos_stock_quant_domain(self, vals):
        return [('product_tmpl_id.available_in_pos', '=', True),('product_tmpl_id.sale_ok', '=', True),('location_id.usage','=','internal')]

    def _sync_pos_product_product_domain(self, vals):
        config = vals['config']
        domain = []
        
        if config.iface_tipproduct:
            domain += [ '|', ('id','=',config.tip_product_id.id) ]

        if config.limit_categories and config.iface_available_categ_ids:
            domain += ['&']

        domain += ['&', '&', ['sale_ok','=',True], ['available_in_pos','=',True],
                '|',['company_id','=',config.company_id.id],['company_id','=',False]]

        if config.limit_categories and config.iface_available_categ_ids:
           domain += [('pos_categ_id', 'in', config.iface_available_categ_ids.ids)]

        return domain

    def _sync_pos_partner_domain(self):
        return []

    def _sync_pos_pricelist_domain(self):
        return []

    def _sync_pos_lot_serial_number_domain(self):
        return  ['|', ['expiration_date','>=', datetime.now().strftime('%Y-%m-%d %H:%M:%S')], ['expiration_date','=', False]];

    def _sync_pos_voucher_domain(self):
        return [['end_date','>', datetime.now().strftime('%Y-%m-%d %H:%M:%S')], ['state','=', 'active']]

    def _sync_pos_coupon_domain(self):
        return [['end_date','>', datetime.now().strftime('%Y-%m-%d %H:%M:%S')], ['state','=', 'active']]

    def _sync_pos_invoice_domain(self, vals):
        config = vals['config']
        domain = ["|",('company_id','=',config.company_id.id),('company_id','=',False)]
        today = datetime.today()
        if config.load_invoices_type == 'last_3_days':
            domain.append(('create_date', '>=', today + timedelta(days=-3)))
        if config.load_invoices_type == 'last_7_days':
            domain.append(('create_date', '>=', today + timedelta(days=-7)))
        if config.load_invoices_type == 'last_1_month':
            domain.append(('create_date', '>=', today + timedelta(days=-30)))
        if config.load_invoices_type == 'last_1_year':
            domain.append(('create_date', '>=', today + timedelta(days=-365)))
        if 'account.move' in vals:
            domain += [('write_date','>', datetime.strptime(vals['account.move'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        return domain

    def _sync_pos_invoice_line_domain(self, vals):
        config = vals['config']
        domain = ["|",('company_id','=',config.company_id.id),('company_id','=',False)]
        today = datetime.today()
        if config.load_invoices_type == 'last_3_days':
            domain.append(('move_id.create_date', '>=', today + timedelta(days=-3)))
        if config.load_invoices_type == 'last_7_days':
            domain.append(('move_id.create_date', '>=', today + timedelta(days=-7)))
        if config.load_invoices_type == 'last_1_month':
            domain.append(('move_id.create_date', '>=', today + timedelta(days=-30)))
        if config.load_invoices_type == 'last_1_year':
            domain.append(('move_id.create_date', '>=', today + timedelta(days=-365)))
        if 'account.move' in vals:
            domain += [('move_id.write_date','>', datetime.strptime(vals['account.move'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        return domain

    def _sync_pos_pos_order_domain(self, vals):
        config = vals['config']
        domain = ["|",('company_id','=',config.company_id.id), ('company_id','=',False), ('config_id','=',config.id)]
        if 'pos.order' in vals:
            domain += [('write_date','>',vals['pos.order'])]
        return domain

    def _sync_pos_pos_order_line_domain(self, vals, pos_order_ids=[]):
        config = vals['config']
        domain = ["|",('company_id','=',config.company_id.id), ('company_id','=',False), ('order_id','in',pos_order_ids)]
        return domain

    def _sync_pos_pos_payment_domain(self, vals, pos_order_ids=[]):
        config = vals['config']
        domain = ["|",('company_id','=',config.company_id.id), ('company_id','=',False), ('pos_order_id','in',pos_order_ids)]
        return domain


    def auto_sync_product_stock(self, vals):
        config = self.env['pos.config'].browse(vals['pos_config_id'])
        vals['config'] = config
        result = { 'stock_quant': [], 'stock_quant_count': 0, }
        if not config.is_auto_sync_product_stock:
            return result

        last_write_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        if vals.get('stock.quant'):
            last_write_date = vals['stock.quant']

        limit = vals['limit']
        offset = vals['offset']
        domain = self._sync_pos_stock_quant_domain(vals)
        domain += [('write_date','>', datetime.strptime(last_write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        # field_list = self.get_fields_by_model('stock.quant')
        field_list = [
            'write_date', 'active', 'display_name', 'location_id', 'product_uom_id', 'company_id', 
            'lot_id', 'product_id', 'product_tmpl_id', 'tracking', 'warehouse_id', 'quantity'
        ]
        result['stock_quant_count'] = self.env['stock.quant'].with_context(active_test=False).search_count(domain)
        if result['stock_quant_count'] > 0:
            result['stock_quant'] = self.env['stock.quant'].with_context(active_test=False).search_read(domain, fields=field_list, order='id asc', limit=limit, offset=offset)
        return result

    def auto_sync_products(self, vals):
        config = self.env['pos.config'].browse(vals['pos_config_id'])
        vals['config'] = config
        result = { 'product_product': [], 'product_product_count': 0, }
        if not config.is_auto_sync_product:
            return result

        last_write_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        if vals.get('product.product'):
            last_write_date = vals['product.product']

        limit = vals['limit']
        offset = vals['offset']
        domain = self._sync_pos_product_product_domain(vals)
        domain += [('write_date','>', datetime.strptime(last_write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = [ 'id', 'write_date', 'product_tmpl_id', 'name', 'display_name', 'pos_categ_id', 'lst_price', 'barcode']
        result['product_product_count'] = self.env['product.product'].search_count(domain)
        if result['product_product_count'] > 0:
            result['product_product'] = self.env['product.product'].search_read(domain, fields=field_list, order='id asc', limit=limit, offset=offset)
        return result

    def auto_sync_pricelist(self, vals):
        config = self.env['pos.config'].browse(vals['pos_config_id'])
        vals['config'] = config
        result = { 'product_pricelist_item': [], 'product_pricelist_item_count': 0, }
        if not config.is_auto_sync_pricelist:
            return result

        last_write_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        if vals.get('product.pricelist.item'):
            last_write_date = vals['product.pricelist.item']

        limit = vals['limit']
        offset = vals['offset']
        domain = self._sync_pos_pricelist_domain()
        domain += [('pricelist_id','=', config.pricelist_id.id)]
        domain += [('write_date','>', datetime.strptime(last_write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = [
            'id','product_tmpl_id','product_id','categ_id','base','base_pricelist_id','pricelist_id',
            'price_surcharge','price_discount','price_round','price_min_margin','price_max_margin',
            'company_id','currency_id','date_start','date_end','compute_price','fixed_price',
            'percent_price','price','minimum_price','maximum_price','new_price','pricelist_uom_id',
            'type_surcharge','base_price_info','min_quantity','uom_id','uom_ids','applied_on','pos_category_id',
            'min_price','max_price','name','write_date',
        ]
        result['product_pricelist_item_count'] = self.env['product.pricelist.item'].search_count(domain)
        if result['product_pricelist_item_count'] > 0:
            result['product_pricelist_item'] = self.env['product.pricelist.item'].search_read(domain, fields=field_list, order='id asc', limit=limit, offset=offset)
        return result

    def auto_sync_promotion(self, vals):
        config = self.env['pos.config'].browse(vals['pos_config_id'])
        vals['config'] = config
        result = { 'pos.promotion': [], 'pos_promotion_count': 0 }
        if not config.is_auto_sync_promotion:
            return result

        last_write_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        if vals.get('pos.promotion'):
            last_write_date = vals['pos.promotion']

        limit = vals['limit']
        offset = vals['offset']
        domain = [
            ('end_date','>=',datetime.now().strftime('%Y-%m-%d 00:00:00')),
            ('pos_apply', 'in', config.id)
        ]
        domain += [('write_date','>', datetime.strptime(last_write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        pos_promotion_count = self.env['pos.promotion'].with_context(active_test=False).search_count(domain)
        if not pos_promotion_count:
            return result
        result['pos_promotion_count'] = pos_promotion_count

        remove_fields = ['__last_update', 'write_uid', 'create_uid']
        field_list = self.get_fields_by_model('pos.promotion')
        field_list = [x for x in field_list if x not in remove_fields]
        result['pos.promotion'] = self.env['pos.promotion'].with_context(active_test=False).search_read(domain, fields=field_list, order='id asc', limit=limit, offset=offset)
        promotion_ids = [r['id'] for r in result['pos.promotion']]

        for model in self._pos_promotion_models:
            if model == 'pos.promotion':
                continue
            field_list = self.sudo().get_fields_by_model(model)
            field_list = [x for x in field_list if x not in remove_fields]
            domain = [['promotion_id', 'in', promotion_ids]] 
            records = self.env[model].sudo().with_context(active_test=False).search_read(domain, field_list)
            result[model] = records
        return result

    def auto_sync_coupon(self, vals):
        config = self.env['pos.config'].browse(vals['pos_config_id'])
        vals['config'] = config
        result = { 'pos_coupon': [], 'pos_coupon_count': 0, }
        if not config.is_auto_sync_coupon:
            return result

        last_write_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
        if vals.get('pos.coupon'):
            last_write_date = vals['pos.coupon']

        limit = vals['limit']
        offset = vals['offset']
        domain = self._sync_pos_coupon_domain()
        domain += [('write_date','>', datetime.strptime(last_write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = [
            'id','write_date','name','number','code','type_apply','product_ids',
            'minimum_purchase_quantity','sequence_generate_method',
            'manual_input_sequence','start_date','end_date','no_of_usage',
            'no_of_used','coupon_program_id','company_id','state',
            'reward_type','reward_product_ids','reward_quantity',
            'reward_discount_type','reward_discount_amount','reward_max_discount_amount',
        ]
        result['pos_coupon_count'] = self.env['pos.coupon'].search_count(domain)
        if result['pos_coupon_count'] > 0:
            result['pos_coupon'] = self.env['pos.coupon'].search_read(domain, fields=field_list, order='id asc', limit=limit, offset=offset)
        return result

    def sync_pos_orders(self, vals):
        vals['config'] = self.env['pos.config'].browse(vals['pos_config_id'])
        result = {}

        order_by = 'write_date desc'
        domain = self._sync_pos_pos_order_domain(vals)
        field_list = self.get_fields_by_model('pos.order')
        pos_orders = self.env['pos.order'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        result['pos_order'] = pos_orders
        pos_order_ids = [o['id'] for o in pos_orders if 'id' in o]

        order_by = 'write_date desc'
        domain = self._sync_pos_pos_order_line_domain(vals, pos_order_ids=pos_order_ids)
        field_list = self.get_fields_by_model('pos.order.line')
        result['pos_order_line'] = self.env['pos.order.line'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        
        order_by = 'write_date desc'
        domain = self._sync_pos_pos_payment_domain(vals, pos_order_ids=pos_order_ids)
        # field_list = self.get_fields_by_model('pos.payment')
        field_list = ['name', 'payment_date', 'pos_order_id', 'amount', 'payment_method_id']
        result['pos_payment'] = self.env['pos.payment'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        return result

    def sync_pos_product(self, vals):
        vals['config'] = self.env['pos.config'].browse(vals['pos_config_id'])
        result = {}

        order_by = 'write_date desc'
        domain = self._sync_pos_product_product_domain(vals)
        if 'product.product' in vals:
            domain += [('write_date','>',vals['product.product'])]
        field_list = self.get_fields_by_model('product.product')
        result['product_product'] = self.env['product.product'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        order_by = 'write_date desc'
        domain = self._sync_pos_product_template_domain(vals)
        if 'product.template' in vals:
            domain += [('write_date','>',vals['product.template'])]
        field_list = self.get_fields_by_model('product.template')
        result['product_template'] = self.env['product.template'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        order_by = 'write_date desc'
        domain = self._sync_pos_stock_quant_domain(vals)
        if 'stock.quant' in vals:
            domain += [('write_date','>',vals['stock.quant'])]
        field_list = self.get_fields_by_model('stock.quant')
        result['stock_quant'] = self.env['stock.quant'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        order_by = 'write_date desc'
        domain = []
        if 'product.brand' in vals:
            domain += [('write_date','>',vals['product.brand'])]
        field_list = self.get_fields_by_model('product.brand')
        result['product_brand'] = self.env['product.brand'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        order_by = 'write_date desc'
        domain = [('product_id.available_in_pos', '=', True)]
        field_list = self.get_fields_by_model('product.template.barcode')
        result['product_template_barcode'] = self.env['product.template.barcode'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        
        return result

    def sync_pos_partner(self, last_write_date=False):
        order_by = 'write_date desc'
        domain = self._sync_pos_partner_domain()
        if last_write_date:
            domain += [('write_date','>', datetime.strptime(last_write_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = self.get_fields_by_model('res.partner')
        result = self.env['res.partner'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        return result 

    def sync_pos_pricelist(self, vals=False):
        result = {}
        order_by = 'write_date desc'
        domain = self._sync_pos_pricelist_domain()
        if 'last_write_date' in vals:
            domain += [('write_date','>', datetime.strptime(vals['last_write_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = self.get_fields_by_model('product.pricelist.item')
        result['product_pricelist_item'] = self.env['product.pricelist.item'].with_context(active_test=False).with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        # Check if pricelist item deleted
        result['product_pricelist_item_ids'] = self.get_childs_of_pricelist(vals['pricelist_id'])
        return result

    def sync_pos_lot_serial_number(self, vals):
        result = {}
        order_by = 'write_date desc'
        domain = self._sync_pos_lot_serial_number_domain()
        if 'last_write_date' in vals:
            domain += [('write_date','>', datetime.strptime(vals['last_write_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = self.get_fields_by_model('stock.production.lot')
        result['stock_production_lot'] = self.env['stock.production.lot'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        return result

    def sync_pos_voucher(self, vals):
        result = {}
        order_by = 'write_date desc'
        domain = self._sync_pos_voucher_domain()
        if 'last_write_date' in vals:
            domain += [('write_date','>', datetime.strptime(vals['last_write_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = self.get_fields_by_model('pos.voucher')
        result['pos.voucher'] = self.env['pos.voucher'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        return result

    def sync_pos_coupon(self, vals):
        result = {}
        order_by = 'write_date desc'
        domain = self._sync_pos_coupon_domain()
        if 'last_write_date' in vals:
            domain += [('write_date','>', datetime.strptime(vals['last_write_date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999'))]
        field_list = [
            'id','write_date','name','number','code','type_apply','product_ids','minimum_purchase_quantity','sequence_generate_method',
            'manual_input_sequence','start_date','end_date','no_of_usage','no_of_used','coupon_program_id','company_id','state','reward_type',
            'reward_product_ids','reward_quantity','reward_discount_type','reward_discount_amount','reward_max_discount_amount'
        ]
        result['pos.coupon'] = self.env['pos.coupon'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)
        return result


    def sync_pos_promotion(self, vals):
        results = {}
        write_date = False
        if vals.get('pos.promotion'):
            write_date = datetime.strptime(vals['pos.promotion'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.999999')
        config = self.env['pos.config'].sudo().browse(vals['pos_config_id'])

        # Force sync: get all promotions data without checking write_date (slower)
        if vals.get('force_sync') == True:
            promotion_ids = []
            for model in self._pos_promotion_models:
                field_list = self.sudo().get_fields_by_model(model)
                domain = []
                if model == 'pos.promotion':
                    domain += [ 
                        ('active','=',True),
                        ('state', '=', 'active'),
                        ('end_date','>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
                        ('id', 'in', config.promotion_ids.ids)
                    ]
                else:
                    domain = [['promotion_id', 'in', promotion_ids]] 

                records = self.env[model].sudo().search_read(domain, field_list)
                if model == 'pos.promotion':
                    promotion_ids = [r['id'] for r in records]
                results[model] = records
        else:
            promotion_ids = []
            for model in self._pos_promotion_models:
                field_list = self.sudo().get_fields_by_model(model)
                domain = []
                if model == 'pos.promotion':
                    if write_date:
                        domain += [('write_date','>', write_date)]
                    domain += [ 
                        ('active','=',True),
                        ('state', '=', 'active'),
                        ('end_date','>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
                        ('id', 'in', config.promotion_ids.ids)
                    ]
                else:
                    domain = [['promotion_id', 'in', promotion_ids]] 

                records = self.env[model].sudo().search_read(domain, field_list)
                if model == 'pos.promotion':
                    promotion_ids = [r['id'] for r in records]

                    # Double search promotions without checking write_date and promotion_ids previously
                    if vals.get('promotion_ids'):
                        avoid_promotion_ids = promotion_ids + vals['promotion_ids']
                        new_domain = [ 
                            ('active','=',True),
                            ('state', '=', 'active'),
                            ('end_date','>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
                            ('id', 'not in', avoid_promotion_ids),
                            ('id', 'in', config.promotion_ids.ids), # Promotions Applied for selected POS
                        ]
                        new_records = self.env[model].sudo().search_read(new_domain, field_list)
                        if new_records:
                            records += new_records
                            promotion_ids += [nr['id'] for nr in new_records]

                results[model] = records


        # Check if any record deleted
        results['existing_ids_of_promotion_and_childs'] = self.get_existing_ids_of_promotion_and_childs(config)
        return results


    def sync_pos_invoice(self, vals):
        pos_config = self.env['pos.config'].browse(vals['pos_config_id'])
        vals['config'] = pos_config 
        result = {}
 
        order_by = 'write_date desc'
        domain = self._sync_pos_invoice_domain(vals)
        field_list = self.get_fields_by_model('account.move')
        result['account_move'] = self.env['account.move'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        domain = self._sync_pos_invoice_line_domain(vals)
        order_by = 'write_date desc'
        field_list = self.get_fields_by_model('account.move.line')
        result['account_move_line'] = self.env['account.move.line'].with_context(active_test=False).search_read(domain, fields=field_list, order=order_by)

        return result