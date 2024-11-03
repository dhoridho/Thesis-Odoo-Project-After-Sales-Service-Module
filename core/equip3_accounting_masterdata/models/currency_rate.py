import logging
import math
import re
import time
import traceback
from lxml import etree
from odoo import api, fields, models, tools, _
from odoo.addons.base.models.ir_ui_view import (transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,)


def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None

CURRENCY_DISPLAY_PATTERN = re.compile(r'(\w+)\s*(?:\((.*)\))?')


class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'
    
    conversion = fields.Floatrate = fields.Float('Inverse Rate', digits='Currency Rate')
    rate = fields.Float(digits='Currency Rate', default=1.0, help='The rate of the currency to the currency of rate 1')
    mr_rate = fields.Float(digits='Currency Rate', default=1.0, help='The rate of the currency to the currency of rate 1')

    # @api.model
    # def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
    #     result = super(CurrencyRate, self).fields_view_get(
    #         view_id, view_type, toolbar=toolbar, submenu=submenu)
    #     company_id = self.env.context.get("company_id") or self.env.company.id
    #     company_obj = self.env['res.company'].browse(company_id)
    #     doc = etree.XML(result['arch'])
    #     if not company_obj.is_inverse_rate:
    #         for node in doc.xpath("//field[@name='conversion']"):
    #             doc.remove(node)
    #         if view_type == 'tree':
    #             for node in doc.xpath("//field[@name='rate']"):
    #                 doc.remove(node)
    #     else:
    #         if view_type == 'tree':
    #             node = doc.xpath("//field[@name='rate']")[0]
    #             node.set('force_save', '1')
    #             setup_modifiers(node, result['fields']['rate'])
    #         for node in doc.xpath("//field[@name='mr_rate']"):
    #             doc.remove(node)
    #     result['arch'] = etree.tostring(doc, encoding='unicode')
    #     return result

    @api.onchange('conversion')
    def _get_rate_conversion(self):
        for record in self:
            if record.conversion:
                print("if record.conversion:")
                val_rate = float(1) / record.conversion
                record.mr_rate = val_rate
                record.rate = val_rate                

    @api.onchange('mr_rate')
    def _get_rate_mr_rate(self):
        for record in self:
            if record.mr_rate:
                print("if record.mr_rate:")
                record.conversion = float(1) / record.mr_rate
                record.rate = record.mr_rate
                

    @api.onchange('rate')
    def _get_rate_rate(self):
        for record in self:
            if record.rate:
                print("if record.rate:")
                record.conversion = float(1) / record.rate
                record.mr_rate = record.rate


class Currency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    symbol = fields.Char(tracking=True)
    rate = fields.Float(tracking=True, digits='Currency Rate')
    rate_ids = fields.One2many(tracking=True)
    rounding = fields.Float(tracking=True)
    decimal_places = fields.Integer(tracking=True)
    active = fields.Boolean(default=True)
    position = fields.Selection(tracking=True)
    date = fields.Date(tracking=True)
    currency_unit_label = fields.Char(tracking=True)
    currency_subunit_label = fields.Char(tracking=True)
    conversion = fields.Float(compute='_compute_current_conversion', string='Inverse Rate', digits=0)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(Currency, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu)
        company_id = self.env.context.get("company_id") or self.env.company.id
        company_obj = self.env['res.company'].browse(company_id)
        doc = etree.XML(result['arch'])
        if not company_obj.is_inverse_rate:
            if view_type == 'form':
                node = doc.xpath("//field[@name='conversion']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['conversion'])
        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    def _get_conversion(self, company, date):
        if not self.ids:
            return {}
        self.env['res.currency.rate'].flush(['conversion', 'currency_id', 'company_id', 'name'])
        query = """SELECT c.id,
                        COALESCE((SELECT r.conversion FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS conversion
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    @api.depends('rate_ids.conversion', 'rate_ids.mr_rate')
    def _compute_current_conversion(self):
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = self._get_conversion(company, date)
        for currency in self:
            currency.conversion = currency_rates.get(currency.id) or 1.0

