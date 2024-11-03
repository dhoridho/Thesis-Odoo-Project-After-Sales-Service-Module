# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning


class InsuranceCompany(models.Model):
    _name = 'hms.insurance.company'
    _description = "Insurance Company"
    _inherits = {
        'res.partner': 'partner_id',
    }

    description = fields.Text()
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete='restrict', required=True)

    #ACS NOTE: To avoid dependcay issue this code is here. 
    #Move to related module if new one is creatd.
    @api.model
    def GetInsuranceCompany(self, args, **kwargs):
        """
        var model = 'hms.insurance.company';
        var method = 'GetInsuranceCompany';

        var args = [
            { }
        ];
        """
        insurance_companies = self.sudo().search([])
        insurance_company_data = []
        for ic in insurance_companies:
            insurance_company_data.append({
                'id': ic.id,
                'name': ic.name,
            })
        return insurance_company_data


class Insurance(models.Model):
    _name = 'hms.patient.insurance'
    _description = "Patient Insurance"
    _rec_name = 'policy_number'
    
    patient_id = fields.Many2one('hms.patient', string ='Patient', ondelete='restrict', required=True)
    insurance_company_id = fields.Many2one('hms.insurance.company', string ="Insurance Company", required=True)
    policy_number = fields.Char(string ="Policy Number", required=True)
    insured_value = fields.Float(string ="Insured Value")
    validity = fields.Date(string="Validity")
    active = fields.Boolean(string="Active", default=True)
    note = fields.Text("Notes")

    allow_appointment_insurance = fields.Boolean(string="Insured Appointments", default=False)
    app_insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fix', 'Fix-amount')], 'Insurance Type', default='percentage', required=True)
    app_insurance_amount = fields.Float(string="Co-payment", help="The patient should pay specific amount 50QR")
    app_insurance_percentage = fields.Float(string="Insured Percentage")
    app_insurance_limit = fields.Float(string="Appointment Insurance Limit")
    create_claim = fields.Boolean(string="Create Claim", default=False)

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
        help="If you change the pricelist, only newly added lines will be affected.")
    company_id = fields.Many2one('res.company', 'Hospital', default=lambda self: self.env.user.company_id.id)

    @api.onchange('insurance_company_id')
    def onchange_insurance_company(self):
        if self.insurance_company_id and self.insurance_company_id.property_product_pricelist:
            self.pricelist_id = self.insurance_company_id.property_product_pricelist.id


class InsuranceTPA(models.Model):
    _name = 'insurance.tpa'
    _description = "Insurance TPA"
    _inherits = {
        'res.partner': 'partner_id',
    }

    partner_id = fields.Many2one('res.partner', 'Partner', required=True, ondelete='restrict')


class InsuranceChecklistTemp(models.Model):
    _name = 'hms.insurance.checklist.template'
    _description = "Insurance Checklist Template"

    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)


class RequiredDocuments(models.Model):
    _name = 'hms.insurance.req.doc'
    _description = "Insurance Req Doc"
    
    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)


class InsuCheckList(models.Model):
    _name="hms.insurance.checklist"
    _description = "Insurance Checklist"

    name = fields.Char(string="Name")
    is_done = fields.Boolean(string="Y/N", default=False)
    remark = fields.Char(string="Remarks")
    claim_id = fields.Many2one("hms.insurance.claim", string="Claim")


class SplitInvoiceWizard(models.TransientModel):
    _inherit = 'split.invoice.wizard'

    @api.model
    def create(self, values):
        insurance_id = self._context.get('insurance_id')
        insurance_type = self._context.get('insurance_type')
        insurance_amount = self._context.get('insurance_amount')
        if insurance_id and insurance_type=='fix':
            insurance_id = self.env['hms.patient.insurance'].browse(insurance_id)
            active_record = self.env['account.move'].browse(self._context.get('active_id'))
            lines = []
            app_insurance_amount = insurance_amount
            rem_insurance_amount = insurance_amount
            invoice_line = active_record.invoice_line_ids[0]
            for line in active_record.invoice_line_ids:
                if app_insurance_amount and rem_insurance_amount:
                    if rem_insurance_amount<=line.price_unit:
                        price_unit = line.price_unit - rem_insurance_amount
                        rem_insurance_amount = 0
                    else:
                        price_unit = line.price_unit
                        rem_insurance_amount -= price_unit
                else:
                    price_unit = line.price_unit

                lines.append((0,0,{
                    'name': line.name,
                    'product_id': line.product_id and line.product_id.id or False,
                    'line_id': line.id,
                    'quantity': line.quantity,
                    'price': line.price_unit,
                    'qty_to_split': 1,
                    'price_to_split': price_unit,
                    'display_type': line.display_type,
                }))
            values.update({'split_selection': 'lines', 'line_split_selection': 'price', 'line_ids': lines})

        return super(SplitInvoiceWizard, self).create(values)
