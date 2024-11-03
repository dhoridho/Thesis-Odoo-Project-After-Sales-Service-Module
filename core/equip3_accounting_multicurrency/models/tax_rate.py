import logging
import math
import re
import time
import traceback
from lxml import etree
from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)
from odoo import api, fields, models, http, tools, _
import json
import requests
import re
from datetime import date



_logger = logging.getLogger(__name__)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)


class CurrencyTaxRate(models.Model):
    _name = "res.currency.tax"
    _description = "Currency Tax Rate"
    _order = "name desc"

    name = fields.Date(string='Date', required=True, index=True, default=lambda self: fields.Date.today())
    rate = fields.Float(digits='Currency Rate', default=1.0, help='The rate of the currency to the currency of rate 1')
    conversion = fields.Float('Inverse Rate', digits='Currency Rate')
    mr_rate = fields.Float(digits='Currency Rate', default=1.0, help='The rate of the currency to the currency of rate 1')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, required=True, ondelete="cascade")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_name_per_day', 'unique (name,currency_id,company_id)', 'Only one currency rate per day allowed!'),
        ('currency_rate_check', 'CHECK (rate>0)', 'The currency rate must be strictly positive.'),
    ]

    @api.onchange('conversion')
    def _get_rate_conversion(self):
        for record in self:
            if record.conversion:
                val_rate = float(1) / record.conversion
                record.rate = val_rate
                record.mr_rate = val_rate

    @api.onchange('mr_rate')
    def _get_rate_mr_rate(self):
        for record in self:
            if record.mr_rate:
                record.rate = record.mr_rate
                record.conversion = float(1) / record.mr_rate

    @api.onchange('rate')
    def _get_rate_rate(self):
        for record in self:
            if record.rate:
                record.mr_rate = record.rate
                record.conversion = float(1) / record.rate


    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(CurrencyTaxRate, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu)
        company_id = self.env.context.get("company_id") or self.env.company.id
        company_obj = self.env['res.company'].browse(company_id)
        doc = etree.XML(result['arch'])
        if company_obj.is_taxes_rate and company_obj.is_inverse_rate:
            for node in doc.xpath("//field[@name='mr_rate']"):
                doc.remove(node)
        else:
            for node in doc.xpath("//field[@name='conversion']"):
                doc.remove(node)
            if view_type == 'tree':
                for node in doc.xpath("//field[@name='rate']"):
                    doc.remove(node)
        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator in ['=', '!=']:
            try:
                date_format = '%Y-%m-%d'
                if self._context.get('lang'):
                    lang_id = self.env['res.lang']._search([('code', '=', self._context['lang'])], access_rights_uid=name_get_uid)
                    if lang_id:
                        date_format = self.browse(lang_id).date_format
                name = time.strftime('%Y-%m-%d', time.strptime(name, date_format))
            except ValueError:
                try:
                    args.append(('rate', operator, float(name)))
                except ValueError:
                    return []
                name = ''
                operator = 'ilike'
        return super(CurrencyTaxRate, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)


class Currency(models.Model):
    _inherit = "res.currency"

    tax_rate_ids = fields.One2many('res.currency.tax', 'currency_id', tracking=True, string='Rates')
    tax_rate = fields.Float(digits='Currency Rate', compute='_compute_current_tax_rate', string='Current Taxes Rate', help='The rate of the currency to the currency of rate 1.')
    tax_conversion = fields.Float(digits='Currency Rate', compute='_compute_current_tax_conversion', string='Inverse Taxes Rate')
    is_taxes_rate = fields.Boolean(compute='_compute_get_taxes_rate')

    def _compute_get_taxes_rate(self):
        company_id = self.env.context.get("company_id") or self.env.company.id
        company_obj = self.env['res.company'].browse(company_id)
        for data in self:
            data.is_taxes_rate = company_obj.is_taxes_rate

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(Currency, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu)
        company_id = self.env.context.get("company_id") or self.env.company.id
        company_obj = self.env['res.company'].browse(company_id)
        doc = etree.XML(result['arch'])
        if not company_obj.is_taxes_rate:
            if view_type == 'form':
                node = doc.xpath("//field[@name='tax_conversion']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['tax_conversion'])

                node = doc.xpath("//field[@name='tax_rate']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['tax_rate'])
        if not company_obj.is_inverse_rate:
            if view_type == 'form':
                node = doc.xpath("//field[@name='tax_conversion']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['tax_conversion'])

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    def _get_tax_rate(self, company, date):
        self.env['res.currency.tax'].flush(['rate', 'currency_id', 'company_id', 'name'])
        query = """SELECT c.id,
                        COALESCE((SELECT r.rate FROM res_currency_tax r
                                  WHERE r.currency_id = c.id AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    @api.depends('tax_rate_ids.rate')
    def _compute_current_tax_rate(self):
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = self._get_tax_rate(company, date)
        for currency in self:
            currency.tax_rate = currency_rates.get(currency.id) or 1.0

    def _get_tax_conversion(self, company, date):
        self.env['res.currency.tax'].flush(['conversion', 'currency_id', 'company_id', 'name'])
        query = """SELECT c.id,
                        COALESCE((SELECT r.conversion FROM res_currency_tax r
                                  WHERE r.currency_id = c.id AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS conversion
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    @api.depends('tax_rate_ids.rate')
    def _compute_current_tax_conversion(self):
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = self._get_tax_conversion(company, date)
        for currency in self:
            currency.tax_conversion = currency_rates.get(currency.id) or 1.0

    @api.model
    def _get_conversion_tax_rate(self, from_currency, to_currency, company, date):
        currency_rates = (from_currency + to_currency)._get_tax_rate(company, date)
        res = currency_rates.get(to_currency.id) / currency_rates.get(from_currency.id)
        return res

    def _tax_convert(self, from_amount, to_currency, company, date, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            to_amount = from_amount * self._get_conversion_tax_rate(self, to_currency, company, date)
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount

    def _convert(self, from_amount, to_currency, company, date, round=True, is_tax=False):
        res = super(Currency, self)._convert(from_amount=from_amount, to_currency=to_currency, company=company, date=date, round=round)
        if self.env.company.is_taxes_rate and is_tax:
            res = self._tax_convert(from_amount=from_amount, to_currency=to_currency, company=company, date=date, round=round)
        return res

    # API TO GET CURRENCY FROM BI
    def action_call_bi_api(self):
        is_api_needed = self.env['ir.config_parameter'].get_param('base.is_call_bi_api')
        currency_api_log_obj = self.env['currency.log.api']
        print (is_api_needed, 'fffgg')
        if is_api_needed:

            type_bi_currency = self.env['ir.config_parameter'].get_param('base.type_bi_currency', 'average')
            active_currencies = self.search([('active', '=', 'True')])
            currency_line_obj = self.env['res.currency.rate']
            for currency in active_currencies:
                today_rate = currency_line_obj.search([('name', '=', date.today()),("currency_id", "=", currency.id)])
                new_currency_val = False
                if currency.active and not today_rate:
                    print("system will pull data on BI for Currency - ", currency.name, "on" ,date.today().strftime("%Y-%m-%d"))
                    currency_mts = currency.name
                    if currency_mts == 'IDR':
                        currency_mts = self.env.company.currency_id.name

                    startdate = date.today().strftime("%Y-%m-%d")
                    enddate = date.today().strftime("%Y-%m-%d")
                    url = "https://www.bi.go.id/biwebservice/wskursbi.asmx/getSubKursLokal3?mts="+currency_mts+"&startdate="+startdate+"&enddate="+enddate
                    print (url, 'ffggh')
                    res = requests.get(url)
                    buy_currency = re.findall("""<beli_subkurslokal>(.*?)</beli_subkurslokal>""", res.text, re.DOTALL)
                    sell_currency = re.findall("""<jual_subkurslokal>(.*?)</jual_subkurslokal>""", res.text, re.DOTALL)

                    if type_bi_currency == 'average' and buy_currency and sell_currency:
                        new_currency_val = (float(buy_currency[0]) + float(sell_currency[0])) / 2
                    elif type_bi_currency == 'buy' and buy_currency:
                        new_currency_val = buy_currency[0]
                    elif type_bi_currency == 'sell' and sell_currency:
                        new_currency_val = sell_currency[0]

                    if currency_mts == 'USD':
                        print( 'Today Buy Rate is ', new_currency_val)

                    if new_currency_val:
                        final_buy_currency = 1/float(new_currency_val)
                        if currency.name == 'IDR':
                            final_buy_currency = float(new_currency_val)
                        if currency.name == self.env.company.currency_id.name:
                            final_buy_currency = 1
                        remarks = "Currency " + currency_mts + " successfully pulled, Today Buy Rate is " + str(new_currency_val)
                        currency_api_log_obj.create({
                            'name' : 'Get API BI create',
                            'url_get' : url,
                            'response' : 'Success',
                            'remarks' : remarks
                            })

                        currency_line_obj.create({
                            'currency_id' : currency.id,
                            'name' : date.today(),
                            'rate' : final_buy_currency,
                            'mr_rate' : final_buy_currency,
                            'conversion' : float(new_currency_val)
                            })

                if currency.active and today_rate:
                    print("system will pull data on BI for Currency - ", currency.name, "on" ,date.today().strftime("%Y-%m-%d"))
                    currency_mts = currency.name
                    if currency_mts == 'IDR':
                        currency_mts = self.env.company.currency_id.name
                    startdate = date.today().strftime("%Y-%m-%d")
                    enddate = date.today().strftime("%Y-%m-%d")
                    url = "https://www.bi.go.id/biwebservice/wskursbi.asmx/getSubKursLokal3?mts="+currency_mts+"&startdate="+startdate+"&enddate="+enddate
                    res = requests.get(url)
                    buy_currency = re.findall("""<beli_subkurslokal>(.*?)</beli_subkurslokal>""", res.text, re.DOTALL)
                    sell_currency = re.findall("""<jual_subkurslokal>(.*?)</jual_subkurslokal>""", res.text, re.DOTALL)

                    if type_bi_currency == 'average' and buy_currency and sell_currency:
                        new_currency_val = (float(buy_currency[0]) + float(sell_currency[0])) / 2
                    elif type_bi_currency == 'buy' and buy_currency:
                        new_currency_val = buy_currency[0]
                    elif type_bi_currency == 'sell' and sell_currency:
                        new_currency_val = sell_currency[0]

                    if currency_mts == 'USD':
                        print( 'Today Buy Rate is ', new_currency_val)
                    if new_currency_val:
                        final_buy_currency = 1/float(new_currency_val)
                        if currency.name == 'IDR':
                            final_buy_currency = float(new_currency_val)
                            print (final_buy_currency, 'final_buy_currency')
                        print("currency updated")
                        if currency.name == self.env.company.currency_id.name:
                            final_buy_currency = 1
                        remarks = "Currency " + currency_mts + " successfully pulled, Today Buy Rate is  " + str(new_currency_val)
                        currency_api_log_obj.create({
                            'name' : 'Get API BI Update',
                            'url_get' : url,
                            'response' : 'Success',
                            'remarks' : remarks
                            })
                        today_rate.write({
                            'rate' : final_buy_currency,
                            'conversion' : float(new_currency_val),
                            'mr_rate' : final_buy_currency,
                            })


    # API TO GET CURRENCY FROM Kemenkeu
    def action_call_kemenkeu_api(self):
        is_api_needed = self.env['ir.config_parameter'].get_param('base.is_call_kemenkeu_api')
        access_token = self.env['ir.config_parameter'].get_param('base.token_kemenkeu_api')
        currency_api_log_obj = self.env['currency.log.api']
        buy_currency = False
        if is_api_needed:
            currency_company = self.env.user.company_id.currency_id.id
            active_currencies = self.search([('active', '=', 'True'),('id','!=',currency_company)])
            currency_line_obj = self.env['res.currency.tax']
            for currency in active_currencies:
                today_rate = currency_line_obj.search([('name', '=', date.today()),("currency_id", "=", currency.id)])

                if currency.active and not today_rate:
                    print("system will pull data on BI for Currency - ", currency.name, "on" ,date.today().strftime("%Y-%m-%d"))
                    currency_mts = currency.name
                    startdate = date.today().strftime("%Y%m%d")
                    enddate = date.today().strftime("%Y-%m-%d")
                    # url = "https://www.bi.go.id/biwebservice/wskursbi.asmx/getSubKursLokal3?mts="+currency_mts+"&startdate="+startdate+"&enddate="+enddate
                    url = "https://portal.fiskal.kemenkeu.go.id/api/v1/kurs/get?access-token="+access_token+"&date="+startdate+"&currency="+currency_mts
                    print (url, 'urll11')
                    res = requests.get(url)
                    print (res, 'fggh')
                    response = requests.get(url)
                    print (response, 'ffgdds')
                    json_response = json.loads(response.text)
                    if response.status_code == 201 or response.status_code == 200:
                        remarks = "Currency " + currency_mts + " successfully pulled"
                        print (json_response, 'json_response')
                        if json_response['data']:
                            buy_currency = json_response['data'][0]['nilai']
                        else:
                            remarks = 'The Data of '+ currency_mts + ' is empty'


                    elif response.status_code == 401:
                        remarks = json_response['message']
                    print (remarks, 'remarks')
                    print (buy_currency)
                    if buy_currency:
                        final_buy_currency = 1/float(buy_currency)
                        print("currency updated")
                        currency_line_obj.create({
                            'currency_id' : currency.id,
                            'name' : date.today(),
                            'rate' : final_buy_currency,
                            'mr_rate' : final_buy_currency,
                            'conversion' : float(buy_currency),
                            })
                        currency_api_log_obj.create({
                            'name' : 'Get API Kemenkeu create',
                            'url_get' : url,
                            'response' : 'Success',
                            'remarks' : remarks
                            })
                    else:
                        currency_api_log_obj.create({
                            'name' : 'Get API Kemenkeu',
                            'url_get' : url,
                            'response' : 'Failed',
                            'remarks' : remarks
                            })


                if currency.active and today_rate:
                    print("system will pull data on BI for Currency - ", currency.name, "on" ,date.today().strftime("%Y-%m-%d"))
                    currency_mts = currency.name
                    startdate = date.today().strftime("%Y%m%d")
                    enddate = date.today().strftime("%Y-%m-%d")
                    

                    url = "https://portal.fiskal.kemenkeu.go.id/api/v1/kurs/get?access-token="+access_token+"&date="+startdate+"&currency="+currency_mts
                    print (url, 'urll11')
                    res = requests.get(url)
                    print (res, 'fggh')
                    response = requests.get(url)
                    print (response, 'ffgdds')
                    json_response = json.loads(response.text)
                    if response.status_code == 201 or response.status_code == 200:
                        remarks = "Currency " + currency_mts + " successfully pulled"
                        print (json_response, 'json_response')
                        if json_response['data']:
                            buy_currency = json_response['data'][0]['nilai']
                        else:
                            remarks = 'The Data of '+ currency_mts + ' is empty'

                    elif response.status_code == 401:
                        remarks = json_response['message']
                    print (remarks, 'remarks')
                    
                    if buy_currency:
                        final_buy_currency = 1/float(buy_currency)
                        print("currency updated")
                        today_rate.write({
                            'rate' : final_buy_currency,
                            'conversion' : float(buy_currency),
                            'mr_rate' : final_buy_currency,
                            
                            })
                        currency_api_log_obj.create({
                            'name' : 'Get API Kemenkeu create',
                            'url_get' : url,
                            'response' : 'Success',
                            'remarks' : remarks
                            })
                    else:
                        currency_api_log_obj.create({
                            'name' : 'Get API Kemenkeu',
                            'url_get' : url,
                            'response' : 'Failed',
                            'remarks' : remarks
                            })



class CurrencyLogApi(models.Model):
    _name = "currency.log.api"

    name = fields.Char('name')
    url_get = fields.Char('Url Get')
    response = fields.Char('Response')
    remarks = fields.Char('Remarks')
    
    