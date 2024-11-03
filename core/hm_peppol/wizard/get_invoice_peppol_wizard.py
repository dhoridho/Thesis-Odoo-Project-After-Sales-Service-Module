import os

from passlib import context
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, Warning
import base64
import requests
import json
import datetime
from datetime import datetime
from lxml import etree
import xmltodict
import urllib.parse


def get_value_xml(target_tree, xpath, namespaces, index):
    try:
        return target_tree.xpath(xpath, namespaces=namespaces)[index].text
    except IndexError:
        if len(target_tree.xpath(xpath, namespaces=namespaces)) == 0:
            return ""
        else:
            return target_tree.xpath(xpath, namespaces=namespaces)[0].text
    except etree.XPathEvalError:
        return ""


ns = {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
      "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
      "i2": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"}

# Wizard Get Invoice Peppol


class GetInvoicePeppolWizard(models.TransientModel):
    _name = "invoice.peppol.wizard"
    _description = "Get Invoice PEPPOL Wizard Query Invoices by Client Batch Reference - JSON"

    date_from = fields.Date('Date From', required=True)
    date_to = fields.Date('Date To', required=True)

    # Query Invoices by Criteria - JSON@api.multi
    def get_partner(self, peppol_id):
        partner_id = self.env['res.partner'].search([('peppol_id', 'ilike', peppol_id)])
        if partner_id:
            return partner_id[0]
        else:
            return False

    # @api.multi
    def get_invoice_by_creteria_json(self):
        if not self.date_from and self.date_to:
            raise UserError(_('You Must Entry Date From and Date To'))

        d1 = self.date_from
        d1 = d1.strftime('%Y-%m-%d')
        timeFrom = 'timeFrom='+d1+' 00:00:00'

        d2 = self.date_to
        d2 = d2.strftime('%Y-%m-%d')
        timeTo = '&timeTo='+d2+' 23:59:59'

        data_company = self.env['res.users'].browse(self.env.uid).company_id
        base_uri = data_company.base_uri
        api_version = data_company.api_version
        username = data_company.api_key
        password = data_company.api_secret
        api_key = (username + ':' + password).encode()
        basic_auth = base64.b64encode(api_key)
        company_peppol_id = data_company.partner_id.peppol_id
        receiver = "&receiver={}".format(company_peppol_id)

        invoice_list = []
        invoicing_list = []
        params = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Authorization': 'Basic %s' % basic_auth.decode(),
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        get_datas = requests.get(base_uri+'/business/' + api_version + '/invoices.json?type=1&status=send success&pageSize=100&' + timeFrom + timeTo + receiver, headers=params)
        print('Response Status Code ', get_datas.status_code, get_datas.text)
        if get_datas.status_code != 200:
            return_value = json.loads(get_datas.text)
            raise Warning(_("Operation Failed!\n{}".format(json.dumps(return_value, indent=2))))

        if get_datas.status_code == 200:
            data = json.loads(get_datas.content.decode("utf-8"))
            for key, value in data.items():
                # print (key, value)
                if isinstance(value, list):
                    for val in value:
                        if val.get("documentNo", False) and val.get("documentNo") not in invoice_list \
                                and val.get("status",False) == "Send Success" :
                            invoice_list.append(val.get("documentNo"))
        ##Start Download Invoices##
        for InvoiceNo in invoice_list:
            print(InvoiceNo)
            InvoiceNo = urllib.parse.quote(InvoiceNo, safe='')
            download = requests.get(base_uri+'/business/' + api_version + '/invoices/%s.xml' % InvoiceNo, headers=params)
            if download.status_code == 200:
                my_dict = xmltodict.parse(download.content)
                # print(json.dumps(my_dict, indent=4, skipkeys=True))

                xmlObject = etree.fromstring(download.content)
                xmlTree = xmlObject.getroottree()
                index = 0
                invoices_list = []
                partner = False
                HeaderTittle = ['ID', 'Date', 'DueDate', 'InvoiceTypeCode', 'DocumentCurrencyCode', 'OrderReference',
                                'AccountingSupplier', 'AccountingCustomer', 'PaymentTerms', 'TaxTotal', 'TaxSubTotalCateg',
                                'TaxableAmount', 'TaxAmount', 'LineExtensionAmount', 'TaxExclusiveAmount', 'TaxInclusiveAmount',
                                'PayableAmount', 'InvoiceLineID', 'InvoiceLineQty', 'InvoiceLineAmt', 'InvoiceLinePrice']
                for invoice_xml in xmlTree.findall("//cac:Price", namespaces=ns):
                    # print(invoice_xml)
                    tax_shceme_id = None
                    try :
                        tax_shceme_id = my_dict["Invoice"]["cac:TaxTotal"]["cac:TaxSubtotal"]["cac:TaxCategory"]["cbc:ID"]["@schemeID"]
                    except :
                        pass
                    invoices_list.append([
                        my_dict["Invoice"]["cbc:ID"],
                        my_dict["Invoice"]["cbc:IssueDate"],
                        my_dict["Invoice"]["cbc:DueDate"],
                        my_dict["Invoice"]["cbc:InvoiceTypeCode"],
                        my_dict["Invoice"]["cbc:DocumentCurrencyCode"],
                        my_dict["Invoice"]["cac:OrderReference"]["cbc:ID"],
                        my_dict["Invoice"]["cac:AccountingSupplierParty"]["cac:Party"]["cbc:EndpointID"]["#text"],
                        my_dict["Invoice"]["cac:AccountingCustomerParty"]["cac:Party"]["cbc:EndpointID"]["#text"],
                        my_dict["Invoice"]["cac:PaymentTerms"]["cbc:Note"],
                        my_dict["Invoice"]["cac:TaxTotal"]["cbc:TaxAmount"]["#text"],
                        tax_shceme_id,
                        my_dict["Invoice"]["cac:TaxTotal"]["cac:TaxSubtotal"]["cbc:TaxableAmount"]["#text"],
                        my_dict["Invoice"]["cac:TaxTotal"]["cac:TaxSubtotal"]["cbc:TaxAmount"]["#text"],
                        my_dict["Invoice"]["cac:LegalMonetaryTotal"]["cbc:LineExtensionAmount"]["#text"],
                        my_dict["Invoice"]["cac:LegalMonetaryTotal"]["cbc:TaxExclusiveAmount"]["#text"],
                        my_dict["Invoice"]["cac:LegalMonetaryTotal"]["cbc:TaxInclusiveAmount"]["#text"],
                        my_dict["Invoice"]["cac:LegalMonetaryTotal"]["cbc:PayableAmount"]["#text"],
                        my_dict["Invoice"]["cac:InvoiceLine"]["cbc:ID"],
                        my_dict["Invoice"]["cac:InvoiceLine"]["cbc:InvoicedQuantity"]["#text"],
                        my_dict["Invoice"]["cac:InvoiceLine"]["cbc:LineExtensionAmount"]["#text"],
                        my_dict["Invoice"]["cac:InvoiceLine"]["cac:Price"]["cbc:PriceAmount"]["#text"],
                        my_dict["Invoice"]["cac:InvoiceLine"]["cac:Item"]["cbc:Name"],
                        my_dict["Invoice"]["cac:AccountingSupplierParty"]["cac:Party"]["cbc:EndpointID"]["@schemeID"],
                    ])
                    index += 1

                if invoices_list:
                    # print(invoices_list)
                    strpeppol_id = (invoices_list[0][22]+':'+invoices_list[0][7])
                    partner = self.get_partner(strpeppol_id)
                    invoice_obj = self.env['account.move']
                    invoice_line_obj = self.env['account.move.line']
                    journal_id = invoice_obj.with_context({'default_move_type': 'in_invoice'}).default_get(['journal_id'])['journal_id']
                    partner_id = False
                    account_id = False
                    if partner:
                        partner_id = partner.id
                        account_id = partner.property_account_payable_id.id
                    new_invoice = invoice_obj.create({
                        'partner_id': partner_id,
                        'journal_id': journal_id,
                        'ref': invoices_list[0][0],
                        'move_type': 'in_invoice',
                        'invoice_date': invoices_list[0][1] or False,
                        'invoice_date_due': invoices_list[0][2] or False,
                    })
                    print ("new_invoice", new_invoice)
                    if new_invoice:
                        inv_line_val = []
                        for inv_line in invoices_list:
                            inv_line_val.append((0,0,{
                                'name': inv_line[17] + "-" + inv_line[21],
                                'quantity': float(inv_line[18]),
                                'price_unit': float(inv_line[20]),
                            }))
                        new_invoice.write({'invoice_line_ids': inv_line_val})
                        new_invoice._onchange_invoice_line_ids()
                        invoicing_list.append(new_invoice.id)
        if invoicing_list :
            return {
                'name': _('Bills'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', invoicing_list)],
            }
