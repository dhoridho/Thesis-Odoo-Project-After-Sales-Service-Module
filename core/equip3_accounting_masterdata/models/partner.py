# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import logging

from psycopg2 import sql, DatabaseError

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from lxml import etree
from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_interest_receivable(self):
        return self.env.ref('equip3_accounting_masterdata.data_interest_customer_account_receivable', raise_if_not_found=False)

    def _default_interest_payable(self):
        return self.env.ref('equip3_accounting_masterdata.data_interest_vendor_account_payable', raise_if_not_found=False)
    
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        idn_id = self.env.ref('base.id') and  self.env.ref('base.id').id or 100
        country =  self.env['res.country'].browse(idn_id)
        if country:
            if country.name != 'Indonesia' or country.code != 'ID':
                country =  self.env['res.country'].search(['|',('name','=','Indonesia'),('code','=','ID')])
                idn_id = country and country.id or 100

        doc = etree.XML(result['arch'])

        field_tin = doc.xpath("//field[@name='tin']")
        if field_tin:
            field_tin[0].set('attrs', "{'invisible' : [('country_id','in',[%s])]}"%(idn_id))
            setup_modifiers(field_tin[0], result['fields']['tin'])

        field_date = doc.xpath("//field[@name='date']")
        if field_date:
            field_date[0].set('attrs', "{'invisible' : ['|',('country_id','in',[%s]),('company_type','!=','person')]}"%(idn_id))
            setup_modifiers(field_date[0], result['fields']['date'])
            
        field_country = doc.xpath("//field[@name='country']")
        if field_country:
            field_country[0].set('attrs', "{'invisible' : ['|',('country_id','in',[%s]),('company_type','!=','person')]}"%(idn_id))
            setup_modifiers(field_country[0], result['fields']['country'])

        field_no_paspor = doc.xpath("//field[@name='no_paspor']")
        if field_no_paspor:
            field_no_paspor[0].set('attrs', "{'invisible' : [('country_id','in',[%s])]}"%(idn_id))
            setup_modifiers(field_no_paspor[0], result['fields']['no_paspor'])

        field_no_kitas = doc.xpath("//field[@name='no_kitas']")
        if field_no_kitas:
            field_no_kitas[0].set('attrs', "{'invisible' : [('country_id','in',[%s])]}"%(idn_id))
            setup_modifiers(field_no_kitas[0], result['fields']['no_kitas'])

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    company_id = fields.Many2one('res.company', string='Company')
    # debtor_id = fields.Many2one('customer.degree.trust', string="Trust Degree", compute="_compute_debtor_id", store=False)
    is_limit_salesperson = fields.Boolean(string='Limit Salesperson', default=False)
    customer_sequence = fields.Char(string="Customer ID", readonly=True, copy=False)
    is_customer = fields.Boolean(string="Is a customer")
    vendor_sequence = fields.Char("Vendor ID", readonly=True, copy=False)
    interest_vendor_account_payable = fields.Many2one('account.account',
        domain="[('company_id', '=', current_company_id)]" , 
        string="Interest Account Payable", 
        default=_default_interest_payable)
    interest_customer_account_receivable = fields.Many2one('account.account',
        domain="[('company_id', '=', current_company_id)]" ,
        string="Interest Account Receivable", 
        default=_default_interest_receivable)
    sign_ebupot_id = fields.Selection(selection=[('pengurus','Pengurus'),('kuasa','Kuasa')], string='Penandatangan BP')
    identity_id = fields.Selection(selection=[('npwp','NPWP'),('nik','NIK')], string='Identitas')
    vat_bp = fields.Char('NPWP')
    nin = fields.Char('NIK')
    user_sign = fields.Char('Nama')
    tax_facility = fields.Selection(selection=[('none','None'),('skb','SKB'),('dtp','DTP'),('pp23','Suket PP23'),('other','Lainnya')], string='Fasilitas')
    doc_number = fields.Char('No. Dokumen')
    other_tax = fields.Char('Fasilitas PPh Lainnya')
    desc_other_tax = fields.Char('Tarif PPh Lainnya')
    
    tin = fields.Char('Tax Identity Number')
    date = fields.Date('Tanggal Lahir Penerima Penghasilan')
    country = fields.Text('Tempat Lahir Penerima Penghasilan')
    no_paspor = fields.Char('No Paspor Penerima Penghasilan')
    no_kitas = fields.Char('No Kitas Penerima Penghasilan')

    visible_vat_bp = fields.Boolean(string='visible_vat_bp', compute='_visible_field')
    visible_nin = fields.Boolean(string='visible_nin', compute='_visible_field')
    visible_doc_number = fields.Boolean(string='visible_doc_number', compute='_visible_field')
    visible_other_tax = fields.Boolean(string='visible_other_tax', compute='_visible_field')
    visible_desc_other_tax = fields.Boolean(string='visible_desc_other_tax', compute='_visible_field')
    visible_date = fields.Boolean(string='visible_date', compute='_visible_field')
    visible_country = fields.Boolean(string='visible_country', compute='_visible_field')
    visible_all = fields.Boolean(string='visible_all', compute='_visible_field')

    # customer_availability = fields.Boolean(string="Customer Availability", default=lambda self: self._default_customer_availability())
    customer_availability = fields.Boolean(string="Customer Availability", compute='_compute_customer_availability')
    invoiced_at_monday = fields.Boolean(string="Mon", default=True)
    invoiced_at_tuesday = fields.Boolean(string="Tue", default=True)
    invoiced_at_wednesday = fields.Boolean(string="Wed", default=True)
    invoiced_at_thursday = fields.Boolean(string="Thu", default=True)
    invoiced_at_friday = fields.Boolean(string="Fri", default=True)
    invoiced_at_saturday = fields.Boolean(string="Sat", default=True)
    invoiced_at_sunday = fields.Boolean(string="Sun", default=True)

    @api.depends('name')
    def _compute_customer_availability(self):
        for record in self:
            config = self.env['ir.config_parameter'].sudo()
            record.customer_availability = config.get_param('customer_availability')

    @api.depends('country_id','identity_id','tax_facility','company_type')
    def _visible_field(self):
        if self.country_id.id == 100 or self.country_id.name =='Indonesia':            
            if self.identity_id not in ['npwp']:
                self.visible_vat_bp =  False
            else:
                self.visible_vat_bp = True

            if self.identity_id not in ['nik']:
                self.visible_nin =  False
            else:
                self.visible_nin = True

            if self.tax_facility not in ['skb','dtp','pp23']:
                self.visible_doc_number =  False
            else:
                self.visible_doc_number = True

            if self.tax_facility not in ['other']:
                self.visible_other_tax =  False
                self.visible_desc_other_tax = False
            else:
                self.visible_other_tax = True
                self.visible_desc_other_tax = True

            if self.company_type != 'person':
                self.visible_date = False
                self.visible_country = False
            else:
                self.visible_date = True
                self.visible_country = True            
            self.visible_all = True
        else:
            self.visible_vat_bp = False
            self.visible_nin = False
            self.visible_doc_number = False
            self.visible_other_tax = False
            self.visible_desc_other_tax = False
            self.visible_date = False
            self.visible_country = False
            self.visible_all = False