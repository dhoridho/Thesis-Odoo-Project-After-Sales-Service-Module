# -*- coding: utf-8 -*-

import logging
import json
import copy

from datetime import datetime

from odoo import api, models, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class PosOrderLog(models.Model):
    _name = "pos.order.log"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Tracking Action of Order"
    _order = 'create_date, name'

    name = fields.Char('Order Number Ref (uid)', required=1, readonly=1)
    order_json = fields.Text('Order Json', readonly=1)
    action = fields.Char(
        'Action',
        help='What POS User action on Order',
        required=1,
        readonly=1,
        tracking=3
    )
    create_date = fields.Datetime('Action Date', required=1, readonly=1)
    write_date = fields.Datetime('Write date', readonly=1)
    config_id = fields.Many2one('pos.config', 'POS Config', readonly=1)
    session_id = fields.Many2one('pos.session', 'POS Session', readonly=1)

    def saveLogActionOfOrder(self, vals):
        return self.create({
            'session_id': vals.get('session_id'),
            'config_id': vals.get('config_id'),
            'name': vals.get('uid'),
            'action': vals.get('action'),
            'order_json': json.dumps(vals.get('order_json'))
        }).id

class PosCallLog(models.Model):
    _rec_name = "call_model"
    _name = "pos.call.log"
    _description = "Log datas of pos sessions"

    min_id = fields.Integer('Min Id', required=1, index=True, readonly=1)
    max_id = fields.Integer('Max Id', required=1, index=True, readonly=1)
    call_domain = fields.Char('Domain', required=1, index=True, readonly=1)
    call_results = fields.Char('Results', readonly=1)
    call_model = fields.Char('Model', required=1, index=True, readonly=1)
    call_fields = fields.Char('Fields', index=True, readonly=1)
    active = fields.Boolean('Active', default=True)
    write_date = fields.Datetime('Write date', readonly=1)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', 'Company',default=lambda self: self.env.company.id)

    def compare_database_write_date(self, model, pos_write_date):
        last_logs = self.search([('call_model', '=', model), ('write_date', '<', pos_write_date)])
        if last_logs:
            _logger.info('POS write date is %s' % pos_write_date)
            _logger.info('Model %s write date is %s' % (model, last_logs[0].write_date))
            return True
        else:
            return False

    def covert_datetime(self, model, datas):  # TODO: function for only 12 and 13
        all_fields = self.env[model].fields_get()
        if all_fields:
            for data in datas:
                for field, value in data.items():
                    if field == 'model':
                        continue
                    if all_fields[field] and all_fields[field]['type'] in ['date', 'datetime'] and value:
                        data[field] = value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return datas


    def refresh_logs(self):
        _logger.info('BEGIN refresh_logs()')
        lastLog = self.env['pos.call.log'].search([], limit=1)
        if lastLog:
            today = datetime.today()
            diffDays = (today - lastLog.write_date).days
            _logger.info('[diffDays] %s' % diffDays)
            if diffDays >= 7:
                self.env['pos.cache.database'].sudo().search([]).unlink()
                logs = self.search([])
                for log in logs:
                    log.refresh_log()
                self.env['pos.session'].sudo().search([
                    ('state', '=', 'opened')
                ]).write({
                    'required_reinstall_cache': True
                })
        _logger.info('END refresh_logs()')
        return True

    @api.model
    def refresh_log(self):
        _logger.info('[BEGIN] refresh_log id %s' % self.id)
        cache_database_object = self.env['pos.cache.database']
        cache_database_object.installing_datas(self.call_model, self.min_id, self.max_id)
        return True


    def update_log_data(self, model_name, records, vals=None, state=None):
        _logger.info('[update_log_data] model_name: %s, records: [%s]' % (model_name, str(records)))

        field_list = []
        domain = []
        if model_name == 'product.product':
            field_list = self.env['pos.cache.database']._product_product_fields()
            domain += [('product_tmpl_id.available_in_pos', '=', True)]
            if state == 'write':
                field_list = ['write_date', 'name', 'lst_price', 'active'] 

        if model_name == 'product.template':
            field_list = self.env['pos.cache.database']._product_template_fields()
            domain += [('available_in_pos', '=', True)]
            if state == 'write':
                field_list = ['write_date', 'name', 'lst_price', 'active'] 

        if model_name == 'res.partner':
            field_list = self.env['pos.cache.database']._res_partner_fields()

        domain += [('id', 'in', records)]
        datas = self.env[model_name].with_context(active_test=False).sudo().search_read(domain, field_list)
        datas = self.env['pos.call.log'].covert_datetime(model_name, datas)
        if not datas:
            return False

        logs = self.env['pos.call.log'].sudo().search([('call_model','=', model_name)])
        for log in logs:
            new_datas = []
            for data in datas:
                if int(log.min_id) <= int(data['id']) <= int(log.max_id):
                    new_datas += [data]
            if new_datas:
                results = {x['id']: x for x in json.loads(log.call_results)}
                for new_data in new_datas:
                    if state == 'unlink':
                        new_data['active'] = False
                    if state == 'write':
                        old_data = copy.deepcopy(results[new_data['id']])
                        for _field in field_list:
                            old_data[_field] = new_data[_field]
                        new_data = old_data

                    results[new_data['id']] = new_data

                new_results = [results[x] for x in results]
                log.write({ 'call_results': json.dumps(new_results) }) 

        return True

class PosQueryLog(models.Model):
    _name = "pos.query.log"
    _description = "POS Query Log"

    name = fields.Text('Query String', readonly=1)
    results = fields.Char('Query Results', readonly=1)
    write_date = fields.Datetime('Updated date', readonly=1)

    def updateQueryLogs(self, vals):
        queryExisted = self.search([('name', '=', vals.get('key'))], limit=1)
        if not queryExisted:
            _logger.info('New Query saved with key: %s' % vals.get('key'))
            self.create({
                'name': vals.get('key'),
                'results': json.dumps(vals.get('result'))
            })
        else:
            queryExisted.write({
                'results': json.dumps(vals.get('result'))
            })
        return True

    def clearLogs(self):
        self.search([]).unlink()
        return True
