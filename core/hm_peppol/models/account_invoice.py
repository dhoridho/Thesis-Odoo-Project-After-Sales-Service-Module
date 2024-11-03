# -*- coding: utf-8 -*-
#from comtypes.automation import _
from passlib import context
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from lxml import etree
import requests
import base64
import uuid
import os
from odoo import models, fields, api
import json


def random_uuid():
    return uuid.uuid1()


class AccountInvoiceLineInherit(models.Model):
    _inherit = 'account.move.line'

    uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    desc_uom = fields.Char(related='uom_id.note',
                           string="Description UoM", readonly=True)


class AccountInvoiceInherit(models.Model):
    _inherit = 'account.move'

    client_ref = fields.Char('Client Ref', readonly=True)
    peppol_status = fields.Selection([('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('none', 'None')],
                                     string="PEPPOL Status", readonly=True, default='none')

    peppol_info = fields.Selection([('pending', 'Pending'),
                                    ('processing', 'Processing'),
                                    ('send_success', 'Send Success'),
                                    ('send_error', 'Send Error'),
                                    ('receive_success', 'Receive Success'),
                                    ('receive_error', 'Receive Error'),
                                    ('none', 'None')],
                                   string="PEPPOL Info", readonly=True, default='none')

    peppol_msg = fields.Char('PEPPOL Message', readonly=True)

    def print_test(self):
        print("Testtt")

    # @api.multi
    def send_invoice_peppol(self):
        print("Testtttt")
        for inv in self:
            ubl_version = "2.1"
            vendor_partner = inv.company_id.partner_id
            customer_partner = inv.partner_id

            if not customer_partner.peppol_id:
                raise Warning(
                    _("PEPPOL ID must be fill in for Customer %s" % customer_partner.name))

            currency_name = str(inv.currency_id.name) or str(
                inv.company_id.currency_id.name)

            xml_namespace = {
                None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            }
            root = etree.Element('Invoice', nsmap=xml_namespace)
            # -----Head XML
            etree.SubElement(root, '{%s}UBLVersionID' % xml_namespace['cbc']).text = ubl_version
            etree.SubElement(root, '{%s}CustomizationID' % xml_namespace['cbc']).text = 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0'
            etree.SubElement(root, '{%s}ProfileID' % xml_namespace['cbc']).text = 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'
            etree.SubElement(root, '{%s}ID' % xml_namespace['cbc']).text = str(inv.name)
            etree.SubElement(root, '{%s}IssueDate' % xml_namespace['cbc']).text = str(inv.invoice_date)
            etree.SubElement(root, '{%s}DueDate' % xml_namespace['cbc']).text = str(inv.invoice_date_due) or str(inv.invoice_date)
            etree.SubElement(root, '{%s}InvoiceTypeCode' % xml_namespace['cbc']).text = '380'
            etree.SubElement(root, '{%s}DocumentCurrencyCode' % xml_namespace['cbc']).text = currency_name
            xml_order_reference = etree.SubElement(root, '{%s}OrderReference' % xml_namespace['cac'])
            etree.SubElement(xml_order_reference, '{%s}ID' % xml_namespace['cbc']).text = 'Odoo ' + (str(inv.company_id.name) or "")
            # -----End of Head XML
            # -----Supplier Party
            xml_supplier = etree.SubElement(root, '{%s}AccountingSupplierParty' % xml_namespace['cac'])  # cac
            xml_supplier_party = etree.SubElement(xml_supplier, '{%s}Party' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_supplier_party, '{%s}EndpointID' % xml_namespace['cbc'], dict({"schemeID": str(vendor_partner.peppol_id[0:vendor_partner.peppol_id.find(':')])})).text = str(vendor_partner.peppol_id[vendor_partner.peppol_id.find(':')+1:])  # cbc
            xml_supplier_party_name = etree.SubElement(xml_supplier_party, '{%s}PartyName' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_supplier_party_name, '{%s}Name' % xml_namespace['cbc']).text = str(vendor_partner.name)  # cbc
            xml_supplier_party_address = etree.SubElement(xml_supplier_party, '{%s}PostalAddress' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_supplier_party_address, '{%s}StreetName' % xml_namespace['cbc']).text = str((vendor_partner.street or "") + " " + (vendor_partner.street2 or "") + " " + (vendor_partner.city or "") + " " + (vendor_partner.state_id.name or ""))  # cbc
            etree.SubElement(xml_supplier_party_address, '{%s}PostalZone' % xml_namespace['cbc']).text = str(vendor_partner.zip)  # cbc
            xml_supplier_party_country = etree.SubElement(xml_supplier_party_address, '{%s}Country' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_supplier_party_country, '{%s}IdentificationCode' % xml_namespace['cbc']).text = str(vendor_partner.country_id.code)  # cbc
            xml_supplier_party_tax = etree.SubElement(xml_supplier_party, '{%s}PartyTaxScheme' % xml_namespace['cac'])
            etree.SubElement(xml_supplier_party_tax, '{%s}CompanyID' % xml_namespace['cbc']).text = (str(inv.company_id.vat) or "")
            xml_supplier_party_tax_code = etree.SubElement(xml_supplier_party_tax, '{%s}TaxScheme' % xml_namespace['cac'])
            etree.SubElement(xml_supplier_party_tax_code,'{%s}ID' % xml_namespace['cbc']).text = 'GST'
            xml_supplier_party_entity = etree.SubElement(xml_supplier_party, '{%s}PartyLegalEntity' % xml_namespace['cac'])
            etree.SubElement(xml_supplier_party_entity, '{%s}RegistrationName' % xml_namespace['cbc']).text = str(vendor_partner.name)
            # -----End of Supplier Party
            # -----Customer Party
            xml_customer = etree.SubElement(root, '{%s}AccountingCustomerParty' % xml_namespace['cac'])
            xml_customer_party = etree.SubElement(xml_customer, '{%s}Party' % xml_namespace['cac'])
            etree.SubElement(xml_customer_party, '{%s}EndpointID' % xml_namespace['cbc'], dict({"schemeID": str(customer_partner.peppol_id[0:customer_partner.peppol_id.find(':')])})).text = str(customer_partner.peppol_id[customer_partner.peppol_id.find(':')+1:])  # cbc
            xml_customer_party_name = etree.SubElement(xml_customer_party, '{%s}PartyName' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_customer_party_name, '{%s}Name' % xml_namespace['cbc']).text = str(customer_partner.name)
            xml_customer_party_address = etree.SubElement(xml_customer_party, '{%s}PostalAddress' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_customer_party_address, '{%s}StreetName' % xml_namespace['cbc']).text = str((customer_partner.street or "") + " " + (customer_partner.street2 or "") + " " + (customer_partner.city or "") + " " + (customer_partner.state_id.name or ""))  # cbc
            etree.SubElement(xml_customer_party_address, '{%s}PostalZone' % xml_namespace['cbc']).text = str(customer_partner.zip)  # cbc
            xml_customer_party_country = etree.SubElement(xml_customer_party_address, '{%s}Country' % xml_namespace['cac'])  # cac
            etree.SubElement(xml_customer_party_country, '{%s}IdentificationCode' % xml_namespace['cbc']).text = str(customer_partner.country_id.code)  # cbc
            xml_customer_party_tax = etree.SubElement(xml_customer_party, '{%s}PartyTaxScheme' % xml_namespace['cac'])
            etree.SubElement(xml_customer_party_tax, '{%s}CompanyID' % xml_namespace['cbc']).text = (str(customer_partner.vat) or "")
            xml_customer_party_tax_code = etree.SubElement(xml_customer_party_tax, '{%s}TaxScheme' % xml_namespace['cac'])
            etree.SubElement(xml_customer_party_tax_code,'{%s}ID' % xml_namespace['cbc']).text = 'GST'
            xml_customer_party_entity = etree.SubElement(xml_customer_party, '{%s}PartyLegalEntity' % xml_namespace['cac'])
            etree.SubElement(xml_customer_party_entity, '{%s}RegistrationName' % xml_namespace['cbc']).text = str(customer_partner.name)
            # -----End of Customer Party
            # -----Payment Term
            xml_payment_term = etree.SubElement(root, '{%s}PaymentTerms' % xml_namespace['cac'])
            etree.SubElement(xml_payment_term, '{%s}Note' % xml_namespace['cbc']).text = str(inv.state)
            # -----End of Payment Term
            # -----Tax
            xml_tax_total = etree.SubElement(root, '{%s}TaxTotal' % xml_namespace['cac'])
            etree.SubElement(xml_tax_total, '{%s}TaxAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv.amount_tax or 0.00)
            # if False and inv.tax_line_ids:
            if inv.line_ids.filtered('tax_repartition_line_id') :
                for inv_tax in inv.line_ids.filtered('tax_repartition_line_id'):
                    xml_tax_subtotal = etree.SubElement(xml_tax_total, '{%s}TaxSubtotal' % xml_namespace['cac'])
                    etree.SubElement(xml_tax_subtotal, '{%s}TaxableAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv_tax.tax_base_amount)
                    etree.SubElement(xml_tax_subtotal, '{%s}TaxAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv_tax.price_total)
                    xml_tax_subtotal_category = etree.SubElement(xml_tax_subtotal, '{%s}TaxCategory' % xml_namespace['cac'])
                    etree.SubElement(xml_tax_subtotal_category,'{%s}ID'%xml_namespace['cbc']).text = inv_tax.tax_line_id.gst_category_code or ""
                    etree.SubElement(xml_tax_subtotal_category, '{%s}Percent' % xml_namespace['cbc']).text = str(inv_tax.tax_line_id.amount)
                    xml_tax_subtotal_category_scheme = etree.SubElement(xml_tax_subtotal_category, '{%s}TaxScheme' % xml_namespace['cac'])
                    etree.SubElement(xml_tax_subtotal_category_scheme,'{%s}ID' % xml_namespace['cbc']).text = "GST" #str(inv_tax.name)
            else:
                xml_tax_subtotal = etree.SubElement(xml_tax_total, '{%s}TaxSubtotal' % xml_namespace['cac'])
                etree.SubElement(xml_tax_subtotal, '{%s}TaxableAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = '0.00'
                etree.SubElement(xml_tax_subtotal, '{%s}TaxAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = '0.00'
                xml_tax_subtotal_category = etree.SubElement(xml_tax_subtotal, '{%s}TaxCategory' % xml_namespace['cac'])
                etree.SubElement(xml_tax_subtotal_category, '{%s}ID' % xml_namespace['cbc']).text = 'ZR'
                etree.SubElement(xml_tax_subtotal_category, '{%s}Percent' % xml_namespace['cbc']).text = '0.00'
                xml_tax_subtotal_category_scheme = etree.SubElement(xml_tax_subtotal_category, '{%s}TaxScheme' % xml_namespace['cac'])
                etree.SubElement(xml_tax_subtotal_category_scheme, '{%s}ID' % xml_namespace['cbc']).text = 'GST'
            # -----End of Tax
            # -----LegalMonetary
            xml_legal_monetary = etree.SubElement(root, '{%s}LegalMonetaryTotal' % xml_namespace['cac'])
            etree.SubElement(xml_legal_monetary, '{%s}LineExtensionAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv.amount_untaxed or 0.00)
            etree.SubElement(xml_legal_monetary, '{%s}TaxExclusiveAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv.amount_untaxed or 0.00)
            etree.SubElement(xml_legal_monetary, '{%s}TaxInclusiveAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv.amount_total or 0.00)
            etree.SubElement(xml_legal_monetary, '{%s}PayableAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv.amount_total or 0.00)
            # -----End of LegalMonetary
            # -----InvoiceLines
            if inv.invoice_line_ids:
                for inv_line in inv.invoice_line_ids:
                    xml_invoice_line = etree.SubElement(root, '{%s}InvoiceLine' % xml_namespace['cac'])
                    etree.SubElement(xml_invoice_line, '{%s}ID' % xml_namespace['cbc']).text = str(inv_line.id)
                    etree.SubElement(xml_invoice_line, '{%s}InvoicedQuantity' % xml_namespace['cbc'], dict({"unitCode": str(inv_line.product_uom_id.uom_code or "")})).text = str(inv_line.quantity)
                    etree.SubElement(xml_invoice_line, '{%s}LineExtensionAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv_line.price_subtotal)
                    xml_invoice_line_item = etree.SubElement(xml_invoice_line, '{%s}Item' % xml_namespace['cac'])
                    etree.SubElement(xml_invoice_line_item, '{%s}Name' % xml_namespace['cbc']).text = str(inv_line.product_id.name or inv_line.name)
                    # if inv.line_ids.filtered('tax_repartition_line_id') :
                    if inv_line.tax_ids :
                        tax_id = inv_line.tax_ids[0]
                        xml_invoice_line_item_tax = etree.SubElement(xml_invoice_line_item, '{%s}ClassifiedTaxCategory' % xml_namespace['cac'])
                        etree.SubElement(xml_invoice_line_item_tax, '{%s}ID' % xml_namespace['cbc']).text = tax_id.gst_category_code or "" #",".join([str(x) for x in inv_line.tax_ids.mapped('gst_category_code')])
                        etree.SubElement(xml_invoice_line_item_tax, '{%s}Percent' % xml_namespace['cbc']).text = str(tax_id.amount) #",".join([str(x) for x in inv_line.tax_ids.mapped('amount')])
                        xml_invoice_line_item_tax_scm = etree.SubElement(xml_invoice_line_item_tax, '{%s}TaxScheme' % xml_namespace['cac'])
                        etree.SubElement(xml_invoice_line_item_tax_scm, '{%s}ID' % xml_namespace['cbc']).text = "GST" #",".join(inv_line.tax_ids.mapped('name'))
                    else :
                        xml_invoice_line_item_tax = etree.SubElement(xml_invoice_line_item, '{%s}ClassifiedTaxCategory' % xml_namespace['cac'])
                        etree.SubElement(xml_invoice_line_item_tax, '{%s}ID' % xml_namespace['cbc']).text = 'ZR'
                        etree.SubElement(xml_invoice_line_item_tax, '{%s}Percent' % xml_namespace['cbc']).text = '0.00'
                        xml_invoice_line_item_tax_scm = etree.SubElement(xml_invoice_line_item_tax, '{%s}TaxScheme' % xml_namespace['cac'])
                        etree.SubElement(xml_invoice_line_item_tax_scm, '{%s}ID' % xml_namespace['cbc']).text = 'GST'
                    xml_invoice_line_price = etree.SubElement(xml_invoice_line, '{%s}Price' % xml_namespace['cac'])
                    etree.SubElement(xml_invoice_line_price, '{%s}PriceAmount' % xml_namespace['cbc'], dict({"currencyID": currency_name})).text = str(inv_line.price_unit)
            # -----End of InvoiceLines

            # Check current working directory.
            folder_path = os.path.dirname(os.path.abspath(__file__))

            xml_object = etree.tostring(root,
                                        pretty_print=True,
                                        xml_declaration=True,
                                        encoding='UTF-8')

            with open(os.path.join(folder_path,'InvPeppol.xml'), 'wb+') as writter:
                try:
                    writter.write(xml_object)
                finally:
                    writter.close()

            data_company = self.env['res.users'].browse(self.env.uid).company_id
            base_uri = data_company.base_uri
            api_version = data_company.api_version
            username = data_company.api_key
            password = data_company.api_secret
            api_key = (username+':'+password).encode()
            basic_auth = base64.b64encode(api_key)
            client_ref = random_uuid()

            headers = {
                "Accept": "*/*",
                'Authorization': 'Basic %s' % basic_auth.decode(),
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }

            url = base_uri+'/business/' + api_version + '/invoices/peppol-invoice-2/%s' % client_ref
            files = [
                ('document', ('file1.xml', open(os.path.join(folder_path,'InvPeppol.xml'), 'rb'), 'text/xml'))
            ]
            response = requests.request(
                "PUT", url, headers=headers, files=files)

            print('Response Status Code ', response.status_code, response.text)

            if (response.status_code == 202):
                data = response.json()
                response_status = data['status']
                response_info = data['info'][0]['status']
                response_msg = data['info'][0]['statusMessage']

                res_status = 'none'
                if response_status == 'Pending':
                    res_status = 'pending'
                if response_status == 'Processing':
                    res_status = 'processing'
                if response_status == 'Completed':
                    res_status = 'completed'

                res_info = 'none'
                if response_info == 'Pending':
                    res_info = 'pending'
                if response_info == 'Processing':
                    res_info = 'processing'
                if response_info == 'Send Success':
                    res_info = 'send_success'
                if response_info == 'Send Error':
                    res_info = 'send_error'
                if response_info == 'Receive Success':
                    res_info = 'receive_success'
                if response_info == 'Receive Error':
                    res_info = 'receive_rrror'

                data_invoice = self.env['account.move'].search([('name', '=', inv.name)])
                data_invoice.write({'client_ref': client_ref,
                                    'peppol_status': res_status,
                                    'peppol_info': res_info,
                                    'peppol_msg': response_msg,
                                    })
        try :
            ## remove xml file after success
            os.remove(os.path.join(folder_path,'InvPeppol.xml'))
        except :
            pass

    # @api.multi
    def get_status_invoice_peppol(self):
        data_company = self.env['res.users'].browse(self.env.uid).company_id
        base_uri = data_company.base_uri
        api_version = data_company.api_version
        username = data_company.api_key
        password = data_company.api_secret
        api_key = (username + ':' + password).encode()
        basic_auth = base64.b64encode(api_key)
        client_ref = self.client_ref

        if client_ref:
            files = {}
            headers = {
                'Authorization': 'Basic %s' % basic_auth.decode(),
                'Content-Type': 'application/json'
            }

            url = base_uri + '/business/' + api_version + \
                '/invoices/peppol-invoice-2/%s.json' % client_ref
            response = requests.request(
                "GET", url, headers=headers, files=files)

            print('Response Status Code ', response.status_code, response.text)

            if (response.status_code == 200):
                data = response.json()
                response_status = data['status']
                response_info = data['info'][0]['status']
                response_msg = data['info'][0]['statusMessage']

                res_status = 'none'
                if response_status == 'Pending':
                    res_status = 'pending'
                if response_status == 'Processing':
                    res_status = 'processing'
                if response_status == 'Completed':
                    res_status = 'completed'

                res_info = 'none'
                if response_info == 'Pending':
                    res_info = 'pending'
                if response_info == 'Processing':
                    res_info = 'processing'
                if response_info == 'Send Success':
                    res_info = 'send_success'
                if response_info == 'Send Error':
                    res_info = 'send_error'
                if response_info == 'Receive Success':
                    res_info = 'receive_success'
                if response_info == 'Receive Error':
                    res_info = 'receive_error'

                data_invoice = self.env['account.move'].search(
                    [('client_ref', '=', client_ref)])
                data_invoice.write({'peppol_status': res_status,
                                    'peppol_info': res_info,
                                    'peppol_msg': response_msg,
                                    })
