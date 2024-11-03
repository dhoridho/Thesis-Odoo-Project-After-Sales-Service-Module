import base64
from datetime import datetime
import hashlib
import json
import sys
import requests
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError
    
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    is_lhdn_submit = fields.Boolean(default=False,copy=False)
    is_lhdn_cancel = fields.Boolean(default=False,copy=False)
    is_lhdn_reject = fields.Boolean(default=False,copy=False)
    is_hide_lhdn = fields.Boolean(compute='_compute_is_hide_lhdn')
    is_hide_lhdn_status = fields.Boolean(compute='_compute_is_hide_lhdn_status')
    uuid = fields.Char(string="UUID")
    e_invoice_status =  fields.Selection([('submitted','Submitted'),('valid','Valid'),('invalid','Invalid'),('cancelled','Cancelled')])
    payload_text = fields.Text()
    
    
    @api.depends('move_type')
    def _compute_is_hide_lhdn(self):
        for data in self:
            account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
            if account_setting:
                if data.move_type != 'out_invoice' or data.state != 'posted' or data.is_lhdn_submit or account_setting.status == 'invalid' or account_setting.tin_status == 'invalid' or not account_setting.tin_status or not account_setting.status:  
                    data.is_hide_lhdn = True
                else:
                    data.is_hide_lhdn = False
            else:
                data.is_hide_lhdn = True
                
    @api.depends('move_type')
    def _compute_is_hide_lhdn_status(self):
        for data in self:
            account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
            if account_setting:
                if data.move_type != 'out_invoice' or data.state != 'posted'  or account_setting.status == 'invalid' or account_setting.tin_status == 'invalid' or not account_setting.tin_status or not account_setting.status:  
                    data.is_hide_lhdn_status = True
                else:
                    data.is_hide_lhdn_status = False
            else:
                data.is_hide_lhdn_status = True
    
    
    def login_lhdn(self):
        # lhdn_url = self.env['ir.config_parameter'].sudo().get_param('equip3_einvoice_integration_my.lhdn_url')
        # lhdn_client_id = self.env['ir.config_parameter'].sudo().get_param('equip3_einvoice_integration_my.lhdn_client_id')
        # lhdn_client_secret = self.env['ir.config_parameter'].sudo().get_param('equip3_einvoice_integration_my.lhdn_client_secret')
        account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
                }
        data = {
            'client_id': account_setting.lhdn_client_id,
            'client_secret': account_setting.lhdn_client_secret,
            'grant_type':'client_credentials',
            'scope':'InvoicingAPI'
            # Add other key-value pairs as needed
            }
        response = requests.post(account_setting.lhdn_url+ "/connect/token", headers=headers, data=data)
        return response
        

    def payload(self):
        self.ensure_one()
        current_time = datetime.now()
        multi_currencies = self.env.user.has_group('base.group_multi_currency')
        
        payload_json =  {
    "_D": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "_A": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "_B": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "Invoice": [
        {
            "ID": [
                {
                    "_": self.name
                }
            ],
            "IssueDate": [
                {
                    "_": self.invoice_date.strftime("%Y-%m-%d")
                }
            ],
            "IssueTime": [
                {
                    "_": current_time.strftime("%H:%M:%SZ")
                }
            ],
            "InvoiceTypeCode": [
                {
                    "_": "01",
                    "listVersionID": "1.0"
                }
            ],
            "DocumentCurrencyCode": [
                {
                    "_": self.env.company.currency_id.name if not multi_currencies else self.currency_id.name
                }
            ],
            "InvoicePeriod": [
                {
                    "StartDate": [
                        {
                            "_": self.period_id.date_start.strftime("%d-%m-%Y")
                        }
                    ],
                    "EndDate": [
                        {
                            "_": self.period_id.date_end.strftime("%d-%m-%Y")
                        }
                    ],
                    "Description": [
                        {
                            "_": ""
                        }
                    ]
                }
            ],
            "BillingReference": [
                {
                    "InvoiceDocumentReference": [
                        {
                            "ID": [
                                {
                                    "_": self.payment_reference
                                }
                            ]
                        }
                    ]
                },
                {
                    "AdditionalDocumentReference": [
                        {
                            "ID": [
                                {
                                    "_": ""
                                }
                            ]
                        }
                    ]
                }
            ],
            "AdditionalDocumentReference": [
                {
                    "ID": [
                        {
                            "_": ""
                        }
                    ],
                    "DocumentType": [
                        {
                            "_": ""
                        }
                    ]
                },
                {
                    "ID": [
                        {
                            "_": ""
                        }
                    ],
                    "DocumentType": [
                        {
                            "_": ""
                        }
                    ],
                    "DocumentDescription": [
                        {
                            "_": ""
                        }
                    ]
                },
                {
                    "ID": [
                        {
                            "_": ""
                        }
                    ],
                    "DocumentType": [
                        {
                            "_": ""
                        }
                    ]
                },
                {
                    "ID": [
                        {
                            "_": ""
                        }
                    ]
                }
            ],
            "AccountingSupplierParty": [
                {
                    "AdditionalAccountID": [
                        {
                            "_": "CPT-CCN-W-211111-KL-000002",
                            "schemeAgencyName": "CertEX"
                        }
                    ],
                    "Party": [
                        {
                            "IndustryClassificationCode": [
                                {
                                    "_": self.company_id.company_registry,
                                    "name": self.company_id.name
                                }
                            ],
                            "PartyIdentification": [
                                {
                                    "ID": [
                                        {
                                            "_":self.company_id.partner_id.partner_tin,
                                            "schemeID": "TIN"
                                        }
                                    ]
                                },
                                {
                                    "ID": [
                                        {
                                            "_": self.company_id.partner_id.partner_brn,
                                            "schemeID": "BRN"
                                        }
                                    ]
                                },
                                 {
                                    "ID": [
                                        {
                                            "_": self.company_id.ttx_registration_number,
                                            "schemeID": "TTX"
                                        }
                                    ]
                                },
                                 {
                                    "ID": [
                                        {
                                            "_": self.company_id.sst_registration_number,
                                            "schemeID": "SST"
                                        }
                                    ]
                                }
                            ],
                            "PostalAddress": [
                                {
                                    "CityName": [
                                        {
                                            "_": self.company_id.partner_id.city
                                        }
                                    ],
                                    "PostalZone": [
                                        {
                                            "_": self.company_id.partner_id.zip
                                        }
                                    ],
                                    "CountrySubentityCode": [
                                        {
                                            "_": "10"
                                        }
                                    ],
                                    "AddressLine": [
                                        {
                                            "Line": [
                                                {
                                                    "_": "Lot 66"
                                                }
                                            ]
                                        },
                                        {
                                            "Line": [
                                                {
                                                    "_": "Bangunan Merdeka"
                                                }
                                            ]
                                        },
                                        {
                                            "Line": [
                                                {
                                                    "_": "Persiaran Jaya"
                                                }
                                            ]
                                        }
                                    ],
                                    "Country": [
                                        {
                                            "IdentificationCode": [
                                                {
                                                    "_": "MYS",
                                                    "listID": "ISO3166-1",
                                                    "listAgencyID": "6"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                            "PartyLegalEntity": [
                                {
                                    "RegistrationName": [
                                        {
                                            "_": self.company_id.name
                                        }
                                    ]
                                }
                            ],
                            "Contact": [
                                {
                                    "Telephone": [
                                        {
                                            "_": self.company_id.phone
                                        }
                                    ],
                                    "ElectronicMail": [
                                        {
                                            "_": self.company_id.email
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "AccountingCustomerParty": [
                {
                    "Party": [
                        {
                            "PostalAddress": [
                                {
                                    "CityName": [
                                        {
                                            "_": self.partner_id.city
                                        }
                                    ],
                                    "PostalZone": [
                                        {
                                            "_": ""
                                        }
                                    ],
                                    "CountrySubentityCode": [
                                        {
                                            "_": "10"
                                        }
                                    ],
                                    "AddressLine": [
                                        {
                                            "Line": [
                                                {
                                                    "_": "Lot 66"
                                                }
                                            ]
                                        },
                                        {
                                            "Line": [
                                                {
                                                    "_": "Bangunan Merdeka"
                                                }
                                            ]
                                        },
                                        {
                                            "Line": [
                                                {
                                                    "_": "Persiaran Jaya"
                                                }
                                            ]
                                        }
                                    ],
                                    "Country": [
                                        {
                                            "IdentificationCode": [
                                                {
                                                    "_": "MYS",
                                                    "listID": "ISO3166-1",
                                                    "listAgencyID": "6"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                            "PartyLegalEntity": [
                                {
                                    "RegistrationName": [
                                        {
                                            "_": self.partner_id.name
                                        }
                                    ]
                                }
                            ],
                            "PartyIdentification": [
                                {
                                    "ID": [
                                        {
                                            "_": self.partner_id.partner_tin,
                                            "schemeID": "TIN"
                                        }
                                    ]
                                },
                                {
                                    "ID": [
                                        {
                                            "_": self.partner_id.partner_brn,
                                            "schemeID": "BRN"
                                        }
                                    ]
                                },
                                {
                                    "ID": [
                                        {
                                            "_": self.partner_id.partner_ttx,
                                            "schemeID": "TTX"
                                        }
                                    ]
                                },
                                {
                                    "ID": [
                                        {
                                            "_": self.partner_id.partner_sst,
                                            "schemeID": "TTX"
                                        }
                                    ]
                                }
                            ],
                            "Contact": [
                                {
                                    "Telephone": [
                                        {
                                            "_": self.partner_id.phone
                                        }
                                    ],
                                    "ElectronicMail": [
                                        {
                                            "_": self.partner_id.email
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "Delivery": [
                {
                    "DeliveryParty": [
                        {
                            "PartyLegalEntity": [
                                {
                                    "RegistrationName": [
                                        {
                                            "_": self.partner_shipping_id.name
                                        }
                                    ]
                                }
                            ],
                            "PostalAddress": [
                                {
                                    "CityName": [
                                        {
                                            "_": self.partner_shipping_id.city
                                        }
                                    ],
                                    "PostalZone": [
                                        {
                                            "_": self.partner_shipping_id.zip
                                        }
                                    ],
                                    "CountrySubentityCode": [
                                        {
                                            "_": ""
                                        }
                                    ],
                                    "AddressLine": [
                                        {
                                            "Line": [
                                                {
                                                    "_": "Lot 66"
                                                }
                                            ]
                                        },
                                        {
                                            "Line": [
                                                {
                                                    "_": "Bangunan Merdeka"
                                                }
                                            ]
                                        },
                                        {
                                            "Line": [
                                                {
                                                    "_": "Persiaran Jaya"
                                                }
                                            ]
                                        }
                                    ],
                                    "Country": [
                                        {
                                            "IdentificationCode": [
                                                {
                                                    "_": "MYS",
                                                    "listID": "ISO3166-1",
                                                    "listAgencyID": "6"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                            "PartyIdentification": [
                                {
                                    "ID": [
                                        {
                                            "_": self.partner_shipping_id.partner_tin,
                                            "schemeID": "TIN"
                                        }
                                    ]
                                },
                                {
                                    "ID": [
                                        {
                                            "_":self.partner_shipping_id.partner_brn,
                                            "schemeID": "BRN"
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    "Shipment": [
                        {
                            "ID": [
                                {
                                    "_": "1234"
                                }
                            ],
                            "FreightAllowanceCharge": [
                                {
                                    "ChargeIndicator": [
                                        {
                                            "_": True
                                        }
                                    ],
                                    "AllowanceChargeReason": [
                                        {
                                            "_": "Service charge"
                                        }
                                    ],
                                    "Amount": [
                                        {
                                            "_": 0,
                                            "currencyID": "MYR"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "PaymentMeans": [
                {
                    "PaymentMeansCode": [
                        {
                            "_": "01"
                        }
                    ],
                    "PayeeFinancialAccount": [
                        {
                            "ID": [
                                {
                                    "_": "1234567890123"
                                }
                            ]
                        }
                    ]
                }
            ],
            "PaymentTerms": [
                {
                    "Note": [
                        {
                            "_": "Payment method is cash"
                        }
                    ]
                }
            ],
            "PrepaidPayment": [
                {
                    "ID": [
                        {
                            "_": "E12345678912"
                        }
                    ],
                    "PaidAmount": [
                        {
                            "_": self.down_payment_amount,
                            "currencyID": "MYR"
                        }
                    ],
                    "PaidDate": [
                        {
                            "_": "2000-01-01"
                        }
                    ],
                    "PaidTime": [
                        {
                            "_": "12:00:00Z"
                        }
                    ]
                }
            ],
            "AllowanceCharge": [
                {
                    "ChargeIndicator": [
                        {
                            "_": False
                        }
                    ],
                    "AllowanceChargeReason": [
                        {
                            "_": "Sample Description"
                        }
                    ],
                    "Amount": [
                        {
                            "_": 0,
                            "currencyID": "MYR"
                        }
                    ]
                },
                {
                    "ChargeIndicator": [
                        {
                            "_": True
                        }
                    ],
                    "AllowanceChargeReason": [
                        {
                            "_": "Service charge"
                        }
                    ],
                    "Amount": [
                        {
                            "_": 0,
                            "currencyID": "MYR"
                        }
                    ]
                }
            ],
            "TaxTotal": [
                {
                    "TaxAmount": [
                        {
                            "_": self.amount_tax,
                            "currencyID": "MYR"
                        }
                    ],
                    "TaxSubtotal": [
                        {
                            "TaxableAmount": [
                                {
                                    "_": self.invoice_line_ids.price_tax,
                                    "currencyID": "MYR"
                                }
                            ],
                            "TaxAmount": [
                                {
                                    "_": self.invoice_line_ids.price_tax,
                                    "currencyID": "MYR"
                                }
                            ],
                            "TaxCategory": [
                                {
                                    "ID": [
                                        {
                                            "_": "01"
                                        }
                                    ],
									"TaxExemptionReason": [
                                        {
                                            "_": "NA"
                                        }
                                    ],
                                    "TaxScheme": [
                                        {
                                            "ID": [
                                                {
                                                    "_": "OTH",
                                                    "schemeID": "UN/ECE 5153",
                                                    "schemeAgencyID": "6"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "LegalMonetaryTotal": [
                {
                    # "LineExtensionAmount": [
                    #     {
                    #         "_": 2000.00,
                    #         "currencyID": "MYR"
                    #     }
                    # ],
                    "TaxExclusiveAmount": [
                        {
                            "_": self.amount_untaxed,
                            "currencyID": "MYR"
                        }
                    ],
                    "TaxInclusiveAmount": [
                        {
                            "_": self.amount_total,
                            "currencyID": "MYR"
                        }
                    ],
                    "AllowanceTotalAmount": [
                        {
                            "_": self.discount_amt_line,
                            "currencyID": "MYR"
                        }
                    ],
                    # "ChargeTotalAmount": [
                    #     {
                    #         "_": 2000.00,
                    #         "currencyID": "MYR"
                    #     }
                    # ],
                    # "PayableRoundingAmount": [
                    #     {
                    #         "_": 1.5,
                    #         "currencyID": "MYR"
                    #     }
                    # ],
                    "PayableAmount": [
                        {
                            "_": self.amount_total,
                            "currencyID": "MYR"
                        }
                    ]
                }
            ],
			"InvoiceLine": [
                {
                    "ID": [
                        {
                            "_": "003"
                        }
                    ],
                    "InvoicedQuantity": [
                        {
                            "_": self.invoice_line_ids.quantity,
                            "unitCode": "C62"
                        }
                    ],
                    "LineExtensionAmount": [
                        {
                            "_": 0,
                            "currencyID": "MYR"
                        }
                    ],
                    "AllowanceCharge": [
                        {
                            "ChargeIndicator": [
                                {
                                    "_": False
                                }
                            ],
                            "AllowanceChargeReason": [
                                {
                                    "_": "Sample Description"
                                }
                            ],
                            "MultiplierFactorNumeric": [
                                {
                                    "_": 0.15
                                }
                            ],
                            "Amount": [
                                {
                                    "_": 0,
                                    "currencyID": "MYR"
                                }
                            ]
                        },
                        {
                            "ChargeIndicator": [
                                {
                                    "_": True
                                }
                            ],
                            "AllowanceChargeReason": [
                                {
                                    "_": "Sample Description"
                                }
                            ],
                            "MultiplierFactorNumeric": [
                                {
                                    "_": 0.1
                                }
                            ],
                            "Amount": [
                                {
                                    "_": 0,
                                    "currencyID": "MYR"
                                }
                            ]
                        }
                    ],
                    "TaxTotal": [
                        {
                            "TaxAmount": [
                                {
                                    "_": self.amount_tax,
                                    "currencyID": "MYR"
                                }
                            ],
                            "TaxSubtotal": [
                                {
                                    "TaxableAmount": [
                                        {
                                            "_": self.invoice_line_ids.price_tax,
                                            "currencyID": "MYR"
                                        }
                                    ],
                                    "TaxAmount": [
                                        {
                                            "_": self.invoice_line_ids.price_tax,
                                            "currencyID": "MYR"
                                        }
                                    ],
									"BaseUnitMeasure": [
                                        {
                                            "_": 1,
                                            "unitCode": "C62"
                                        }
                                    ],
									"PerUnitAmount": [
                                        {
                                            "_": self.invoice_line_ids.price_unit,
                                            "currencyID": "MYR"
                                        }
                                    ],
                                    "TaxCategory": [
                                        {
                                            "ID": [
                                                {
                                                    "_": "01"
                                                }
                                            ],                                           
                                            "TaxExemptionReason": [
                                                {
                                                    "_": "Exempt New Means of Transport"
                                                }
                                            ],
                                            "TaxScheme": [
                                                {
                                                    "ID": [
                                                        {
                                                            "_": "OTH",
                                                            "schemeID": "UN/ECE 5153",
                                                            "schemeAgencyID": "6"
                                                        }
                                                    ]
                                                }
                                            ]

                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    "Item": [
                        {
                            "CommodityClassification": [
                                {
                                    "ItemClassificationCode": [
                                        {
                                            "_": "038",
                                            "listID": "PTC"
                                        }
                                    ]
                                },
                                {
                                    "ItemClassificationCode": [
                                        {
                                            "_": "038",
                                            "listID": "CLASS"
                                        }
                                    ]
                                }
                            ],
                            "Description": [
                                {
                                    "_": "Laptop Peripherals"
                                }
                            ],
                            "OriginCountry": [
                                {
                                    "IdentificationCode": [
                                        {
                                            "_": "MYS"
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    "Price": [
                        {
                            "PriceAmount": [
                                {
                                    "_": self.invoice_line_ids.price_unit,
                                    "currencyID": "MYR"
                                }
                            ]
                        }
                    ],
                    "ItemPriceExtension": [
                        {
                            "Amount": [
                                {
                                    "_": self.invoice_line_ids.price_subtotal,
                                    "currencyID": "MYR"
                                }
                            ]
                        }
                    ]
                }
            ],
		"UBLExtensions": [
        {
          "UBLExtension": [
            {
              "ExtensionURI": [
                {
                  "_": "urn:oasis:names:specification:ubl:dsig:enveloped:xades"
                }
              ],
              "ExtensionContent": [
                {
                  "UBLDocumentSignatures": [
                    # {
                    #   "SignatureInformation": [
                    #     {
                    #       "ID": [
                    #         {
                    #           "_": "urn:oasis:names:specification:ubl:signature:1"
                    #         }
                    #       ],
                    #       "ReferencedSignatureID": [
                    #         {
                    #           "_": "urn:oasis:names:specification:ubl:signature:Invoice"
                    #         }
                    #       ],
                    #       "Signature": [
                    #         {
                    #           "Id": "signature",
                    #           "Object": [
                    #             {
                    #               "QualifyingProperties": [
                    #                 {
                    #                   "Target": "signature",
                    #                   "SignedProperties": [
                    #                     {
                    #                       "SignedSignatureProperties": [
                    #                         {
                    #                           "SigningTime": [
                    #                             {
                    #                               "_": "2024-06-15T08:25:42Z"
                    #                             }
                    #                           ],
                    #                           "SigningCertificate": [
                    #                             {
                    #                               "Cert": [
                    #                                 {
                    #                                   "CertDigest": [
                    #                                     {
                    #                                       "DigestMethod": [
                    #                                         {
                    #                                           "_": "",
                    #                                           "Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
                    #                                         }
                    #                                       ],
                    #                                       "DigestValue": [
                    #                                         {
                    #                                           "_": "KKBSTyiPKGkGl1AFqcPziKCEIDYGtnYUTQN4ukO7G40="
                    #                                         }
                    #                                       ]
                    #                                     }
                    #                                   ],
                    #                                   "IssuerSerial": [
                    #                                     {
                    #                                       "X509IssuerName": [
                    #                                         {
                    #                                           "_": "CN=Trial LHDNM Sub CA V1, OU=Terms of use at http://www.posdigicert.com.my, O=LHDNM, C=MY"
                    #                                         }
                    #                                       ],
                    #                                       "X509SerialNumber": [
                    #                                         {
                    #                                           "_": "162880276254639189035871514749820882117"
                    #                                         }
                    #                                       ]
                    #                                     }
                    #                                   ]
                    #                                 }
                    #                               ]
                    #                             }
                    #                           ]
                    #                         }
                    #                       ]
                    #                     }
                    #                   ]
                    #                 }
                    #               ]
                    #             }
                    #           ],
                    #           "KeyInfo": [
                    #             {
                    #               "X509Data": [
                    #                 {
                    #                   "X509Certificate": [
                    #                     {
                    #                       "_": "MIIFlDCCA3ygAwIBAgIQeomZorO+0AwmW2BRdWJMxTANBgkqhkiG9w0BAQsFADB1MQswCQYDVQQGEwJNWTEOMAwGA1UEChMFTEhETk0xNjA0BgNVBAsTLVRlcm1zIG9mIHVzZSBhdCBodHRwOi8vd3d3LnBvc2RpZ2ljZXJ0LmNvbS5teTEeMBwGA1UEAxMVVHJpYWwgTEhETk0gU3ViIENBIFYxMB4XDTI0MDYwNjAyNTIzNloXDTI0MDkwNjAyNTIzNlowgZwxCzAJBgNVBAYTAk1ZMQ4wDAYDVQQKEwVEdW1teTEVMBMGA1UEYRMMQzI5NzAyNjM1MDYwMRswGQYDVQQLExJUZXN0IFVuaXQgZUludm9pY2UxDjAMBgNVBAMTBUR1bW15MRIwEAYDVQQFEwlEMTIzNDU2NzgxJTAjBgkqhkiG9w0BCQEWFmFuYXMuYUBmZ3Zob2xkaW5ncy5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQChvfOzAofnU60xFO7NcmF2WRi+dgor1D7ccISgRVfZC30Fdxnt1S6ZNf78Lbrz8TbWMicS8plh/pHy96OJvEBplsAgcZTd6WvaMUB2oInC86D3YShlthR6EzhwXgBmg/g9xprwlRqXMT2p4+K8zmyJZ9pIb8Y+tQNjm/uYNudtwGVm8A4hEhlRHbgfUXRzT19QZml6V2Ea0wQI8VyWWa8phCIkBD2w4F8jG4eP5/0XSQkTfBHHf+GV/YDJx5KiiYfmB1nGfwoPHix6Gey+wRjIq87on8Dm5+8ei8/bOhcuuSlpxgwphAP3rZrNbRN9LNVLSQ5md41asoBHfaDIVPVpAgMBAAGjgfcwgfQwHwYDVR0lBBgwFgYIKwYBBQUHAwQGCisGAQQBgjcKAwwwEQYDVR0OBAoECEDwms66hrpiMFMGA1UdIARMMEowSAYJKwYBBAGDikUBMDswOQYIKwYBBQUHAgEWLWh0dHBzOi8vd3d3LnBvc2RpZ2ljZXJ0LmNvbS5teS9yZXBvc2l0b3J5L2NwczATBgNVHSMEDDAKgAhNf9lrtsUI0DAOBgNVHQ8BAf8EBAMCBkAwRAYDVR0fBD0wOzA5oDegNYYzaHR0cDovL3RyaWFsY3JsLnBvc2RpZ2ljZXJ0LmNvbS5teS9UcmlhbExIRE5NVjEuY3JsMA0GCSqGSIb3DQEBCwUAA4ICAQBwptnIb1OA8NNVotgVIjOnpQtowew87Y0EBWAnVhOsMDlWXD/s+BL7vIEbX/BYa0TjakQ7qo4riSHyUkQ+X+pNsPEqolC4uFOp0pDsIdjsNB+WG15itnghkI99c6YZmbXcSFw9E160c7vG25gIL6zBPculHx5+laE59YkmDLdxx27e0TltUbFmuq3diYBOOf7NswFcDXCo+kXOwFfgmpbzYS0qfSoh3eZZtVHg0r6uga1UsMGb90+IRsk4st99EOVENvo0290lWhPBVK2G34+2TzbbYnVkoxnq6uDMw3cRpXX/oSfya+tyF51kT3iXvpmQ9OMF3wMlfKwCS7BZB2+iRja/1WHkAP7QW7/+0zRBcGQzY7AYsdZUllwYapsLEtbZBrTiH12X4XnZjny9rLfQLzJsFGT7Q+e02GiCsBrK7ZHNTindLRnJYAo4U2at5+SjqBiXSmz0DG+juOyFkwiWyD0xeheg4tMMO2pZ7clQzKflYnvFTEFnt+d+tvVwNjTboxfVxEv2qWF6qcMJeMvXwKTXuwVI2iUqmJSzJbUY+w3OeG7fvrhUfMJPM9XZBOp7CEI1QHfHrtyjlKNhYzG3IgHcfAZUURO16gFmWgzAZLkJSmCIxaIty/EmvG5N3ZePolBOa7lNEH/eSBMGAQteH+Twtiu0Y2xSwmmsxnfJyw=="
                    #                     }
                    #                   ],
                    #                   "X509SubjectName": [
                    #                     {
                    #                       "_": "CN=Trial LHDNM Sub CA V1, OU=Terms of use at http://www.posdigicert.com.my, O=LHDNM, C=MY"
                    #                     }
                    #                   ],
                    #                   "X509IssuerSerial": [
                    #                     {
                    #                       "X509IssuerName": [
                    #                         {
                    #                           "_": "CN=Trial LHDNM Sub CA V1, OU=Terms of use at http://www.posdigicert.com.my, O=LHDNM, C=MY"
                    #                         }
                    #                       ],
                    #                       "X509SerialNumber": [
                    #                         {
                    #                           "_": "162880276254639189035871514749820882117"
                    #                         }
                    #                       ]
                    #                     }
                    #                   ]
                    #                 }
                    #               ]
                    #             }
                    #           ],
                    #           "SignatureValue": [
                    #             {
                    #               "_": "TvCMfw5ZpE1jyQZdJADUiELdIGoBwKccK+8XNYZ4s5w1I7w2S9+XEObeUaWDhnwrPq+7P34gxPq5IafMBFjNeCE2UgBSAD/LXzDIwC5GdN/y7QAitiH8fO6g7867cwCIKcJvUtaA0s9rVNDkyr3nd6sSit4QdhuFOIHWsntCyLY6kwCI20fyZb7sJI6XcL3Loxa8fuw7WBT6F9GMW5ikS8gde2tJc+ta2+BixXxbFU3d6eZQp2KlkRH1+H6C2Z1gWUzV8lbGkHTAkAG81MVaTjbMsK2o0Xpu8DHS0uo4/s2qV4RdoVqbGUtf0s7yTptL1nJYNkeJIGdI9tvx8Vi9nA=="
                    #             }
                    #           ],
                    #           "SignedInfo": [
                    #             {
                    #               "SignatureMethod": [
                    #                 {
                    #                   "_": "",
                    #                   "Algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
                    #                 }
                    #               ],
                    #               "Reference": [
                    #                 {
                    #                   "Type": "http://uri.etsi.org/01903/v1.3.2#SignedProperties",
                    #                   "URI": "#id-xades-signed-props",
                    #                   "DigestMethod": [
                    #                     {
                    #                       "_": "",
                    #                       "Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
                    #                     }
                    #                   ],
                    #                   "DigestValue": [
                    #                     {
                    #                       "_": "1oSIpB+0KfIoKlRcdjYuFlM0z5op2LQaM1Tal5BQQds="
                    #                     }
                    #                   ]
                    #                 },
                    #                 {
                    #                   "Type": "",
                    #                   "URI": "",
                    #                   "DigestMethod": [
                    #                     {
                    #                       "_": "",
                    #                       "Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
                    #                     }
                    #                   ],
                    #                   "DigestValue": [
                    #                     {
                    #                       "_": "AjJmhcxvfcDyxkGaoOa3dGYE808OEezUNB5XN69dYxQ="
                    #                     }
                    #                   ]
                    #                 }
                    #               ]
                    #             }
                    #           ]
                    #         }
                    #       ]
                    #     }
                    #   ]
                    # }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
        return payload_json
        
    
    
    def submit_lhdn(self):
        token = self.login_lhdn().json()
        account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
        
        lhdn_url = account_setting.lhdn_url
        
        endpoint_url = lhdn_url+'/api/v1.0/documentsubmissions'
        json_str = json.dumps(self.payload())
        base64_invoice = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        invoice_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        payload = {
        "documents": [
            {
                "format": "JSON",
                "documentHash": invoice_hash,
                "codeNumber": self.name,
                "document": base64_invoice
            }
        ]
        }

        # Set the headers
        headers = {
            'Content-Type': 'application/json'
        }

        headers['Authorization'] = "Bearer " + token['access_token']
        try:
            response = requests.post(endpoint_url, json=payload, headers=headers)
            response_result = response.json()
            print("response.json()")
            print(headers)
            print(response.json())
            print(response.status_code)
            if 'rejectedDocuments' in response_result:
                if response_result['rejectedDocuments']:
                    raise ValidationError(f"{response_result['rejectedDocuments']}")
        except Exception as e:
            tb = sys.exc_info()
            raise UserError(e.with_traceback(tb[2]))
        
        if response.status_code == 202:
            self.is_lhdn_submit = True
            self.uuid = response_result['acceptedDocuments'][0]['uuid']
            self.e_invoice_status = 'submitted'
            self.payload_text = json_str


            # success_message = f"E-Invoice has been submitted to MyInvois Portal. UUID: {self.uuid}"
            # self.message_post(body=success_message, message_type='notification')

            wizard = {
                'name': "E-Invoice Info",
                'type': 'ir.actions.act_window',
                'res_model': 'einvoice.info.wizard',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {'default_name': 'Notification', 'default_message': 'E-Invoice has been submitted to MyInvois Portal'},
            }

            # js = {
            #             'type': 'ir.actions.client',
            #             'tag': 'display_notification',
            #             'params': {
            #                 'title': 'Success',
            #                 'message': 'E-Invoice has been submitted to MyInvois Portal',
            #                 'sticky': False,  # The notification will disappear after some time if set to False
            #             },
            #         }
                    
            return wizard

        else:
            raise ValidationError(response.json())


    # @api.onchange('einvoice_state')
    # def onchange_einvoice_state(self):
    #     if self.einvoice_state == 'submit':
    #         js = {
    #                     'type': 'ir.actions.client',
    #                     'tag': 'display_notification',
    #                     'params': {
    #                         'title': 'Success',
    #                         'message': 'E-Invoice has been submitted to MyInvois Portal',
    #                         'sticky': False,  # The notification will disappear after some time if set to False
    #                     },
    #                 }
                    
    #         return js

    def action_cancel_e_invoice(self):
        for record in self:
            if record.state != 'posted':
                raise UserError("Only posted invoices can be cancelled.")
            token = record.login_lhdn().json()
            headers = {
            'Content-Type': 'application/json'
            }
            headers['Authorization'] = "Bearer " + token['access_token']
            token = self.login_lhdn().json()
            account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
            lhdn_url = account_setting.lhdn_url
            endpoint_url = lhdn_url+f'/api/v1.0/documents/state/{record.uuid}/state'
            payload = {
                "status":"cancelled",
                "reason":"test"
            }
            try:
                response = requests.put(endpoint_url, json=payload, headers=headers)
                response_result = response.json()
                print(payload)
                print("response.json()")
                print(headers)
                print(response.json())
                print(response.status_code)
                record.e_invoice_status = 'cancelled'

            except Exception as e:
                tb = sys.exc_info()
                raise UserError(e.with_traceback(tb[2]))
            
            if response.status_code == 200:
                self.is_lhdn_cancel = True
            else:
                raise ValidationError(response.content)
            

    
    def lhdn_check_invoice(self):
        for record in self:
            account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
            lhdn_url = account_setting.lhdn_url
            token = record.login_lhdn().json()
            endpoint_url = lhdn_url+f'/api/v1.0/documents/{record.uuid}/details'
            headers = {
            'Authorization': f"Bearer {token['access_token']}"
            }
            try:
                response = requests.get(endpoint_url,headers=headers)
                response_result = response.json()
                if response.status_code == 200:
                    response_result = response.json()
                    if 'status' in response_result:
                        print(str(response_result['status']).lower())
                        if str(response_result['status']).lower() == 'invalid':
                            record.e_invoice_status = 'invalid'
                        if str(response_result['status']).lower() == 'valid':
                            record.e_invoice_status = 'valid'
                            
                        
                    #     record.e_invoice_status = response_result['status']
            except Exception as e:
                tb = sys.exc_info()
                raise UserError(e.with_traceback(tb[2]))
            
            

            

    def action_reject_e_invoice(self):
        for record in self:
            if record.state != 'posted':
                raise UserError("Only posted invoices can be Rejected.")
            token = record.login_lhdn().json()
            headers = {
            'Content-Type': 'application/json'
            }

            headers['Authorization'] = "Bearer " + token['access_token']
            token = self.login_lhdn().json()
            account_setting = self.env['accounting.setting.my'].sudo().search([],limit=1)
            lhdn_url = account_setting.lhdn_url
            endpoint_url = lhdn_url+f'/api/v1.0/documents/state/{record.uuid}/state'
            payload = {
                "status":"rejected",
                "reason":"test"
            }
            try:
                response = requests.put(endpoint_url, json=payload, headers=headers)
                response_result = response.json()
                record.payload = payload
                print(payload)
                print("response.json()")
                print(headers)
                print(response.json())
                print(response.status_code)

            except Exception as e:
                tb = sys.exc_info()
                raise UserError(e.with_traceback(tb[2]))
            
            if response.status_code == 200:
                self.is_lhdn_reject = True
            else:
                raise ValidationError(response.content)

        
        
class EinvoiceInfoWizard(models.TransientModel):
    _name = 'einvoice.info.wizard'
    _description = 'E-Invoice Info Wizard'

    name = fields.Char(string="Title")
    message = fields.Text(string="Message")
    
    def action_ok(self):
        return {'type': 'ir.actions.act_window_close'}