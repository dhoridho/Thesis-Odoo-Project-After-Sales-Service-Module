# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning


class ACSPatient(models.Model):
    _inherit = 'hms.patient'

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.claim_count = len(rec.claim_ids)

    claim_ids = fields.One2many('hms.insurance.claim', 'patient_id',string='Claims')
    claim_count = fields.Integer(compute='_rec_count', string='# Claims')
    insurance_ids = fields.One2many('hms.patient.insurance', 'patient_id', string='Insurance')

    def action_insurance_policy(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_insurance.action_hms_patient_insurance")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.id,
        }
        return action

    def action_claim_view(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_insurance.action_insurance_claim")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.id,
        }
        return action


class ACSAppointment(models.Model):
    _inherit = 'hms.appointment'

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    insurance_id = fields.Many2one('hms.patient.insurance', string='Insurance Policy', states=READONLY_STATES)
    claim_id = fields.Many2one('hms.insurance.claim', string='Claim', states=READONLY_STATES)
    insurance_company_id = fields.Many2one('hms.insurance.company', related='insurance_id.insurance_company_id', string='Insurance Company', readonly=True, store=True)
    app_insurance_percentage = fields.Float(related='insurance_id.app_insurance_percentage', string="Insured Percentage", readonly=True)

    def create_invoice(self):
        res = super(ACSAppointment, self).create_invoice()
        if self.invoice_id and self.insurance_id and (self.insurance_id.app_insurance_limit >= self.invoice_id.amount_total or self.insurance_id.app_insurance_limit==0):
            can_be_splited = self.invoice_id.acs_check_auto_spliting_possibility(self.insurance_id)
            if can_be_splited:
                split_context = {
                    'active_model':'account.move', 
                    'active_id': self.invoice_id.id, 
                    'insurance_id': self.insurance_id.id,
                    'insurance_type': self.insurance_id.app_insurance_type,
                    'insurance_amount': self.insurance_id.app_insurance_amount,
                }
                wiz_id = self.env['split.invoice.wizard'].with_context(split_context).create({
                    'split_selection': 'invoice',
                    'percentage': self.app_insurance_percentage,
                    'partner_id': self.insurance_company_id.partner_id.id if self.insurance_company_id.partner_id else self.patient_id.partner_id.id,
                })
                insurance_invoice_id = wiz_id.split_record()
                insurance_invoice_id.write({
                    'appointment_id': self.id,
                    'ref': self.name,
                    'invoice_origin': self.name,
                    'hospital_invoice_type': 'appointment'
                })

                if insurance_invoice_id and self.insurance_id.create_claim:
                    claim_id = self.env['hms.insurance.claim'].create({
                        'patient_id': self.patient_id.id,
                        'insurance_id': self.insurance_id.id,
                        'claim_for': 'appointment',
                        'appointment_id': self.id,
                        'amount_requested': insurance_invoice_id.amount_total,
                    })
                    self.claim_id = claim_id.id
                    insurance_invoice_id.claim_id = claim_id.id
        return res

    def create_consumed_prod_invoice(self):
        res = super(ACSAppointment, self).create_consumed_prod_invoice()
        if self.consumable_invoice_id and self.insurance_id and (self.insurance_id.app_insurance_limit >= self.consumable_invoice_id.amount_total or self.insurance_id.app_insurance_limit==0):
            can_be_splited = self.consumable_invoice_id.acs_check_auto_spliting_possibility(self.insurance_id)
            if can_be_splited:
                split_context = {
                    'active_model':'account.move', 
                    'active_id': self.consumable_invoice_id.id, 
                    'insurance_id': self.insurance_id.id,
                    'insurance_type': self.insurance_id.app_insurance_type,
                    'insurance_amount': self.insurance_id.app_insurance_amount,
                }
                wiz_id = self.env['split.invoice.wizard'].with_context(split_context).create({
                    'split_selection': 'invoice',
                    'percentage': self.app_insurance_percentage,
                    'partner_id': self.insurance_company_id.partner_id.id if self.insurance_company_id.partner_id else self.patient_id.partner_id.id,
                })
                insurance_invoice_id = wiz_id.split_record()
                insurance_invoice_id.write({
                    'appointment_id': self.id,
                    'ref': self.name,
                    'invoice_origin': self.name
                })

                if insurance_invoice_id and self.insurance_id.create_claim:
                    if not self.claim_id:
                        claim_id = self.env['hms.insurance.claim'].create({
                            'patient_id': self.patient_id.id,
                            'insurance_id': self.insurance_id.id,
                            'claim_for': 'appointment',
                            'appointment_id': self.id,
                            'amount_requested': insurance_invoice_id.amount_total,
                        })
                        self.claim_id = claim_id.id
                    insurance_invoice_id.claim_id = self.claim_id.id
        return res

    @api.onchange('patient_id')
    def onchange_patient_id(self):
        super(ACSAppointment, self).onchange_patient_id()
        allow_appointment_insurances = self.patient_id.insurance_ids.filtered(lambda x: x.allow_appointment_insurance)
        pricelist_id = insurance_id = False
        if self.patient_id and allow_appointment_insurances:
            insurance = allow_appointment_insurances[0]
            insurance_id = insurance.id
            pricelist_id = insurance.pricelist_id and insurance.pricelist_id.id or False
    
        self.insurance_id = insurance_id
        self.pricelist_id = pricelist_id


class Invoice(models.Model):
    _inherit = 'account.move'

    claim_id = fields.Many2one('hms.insurance.claim', 'Claim')
    insurance_company_id = fields.Many2one('hms.insurance.company', related='claim_id.insurance_company_id', string='Insurance Company', readonly=True)
    claim_sheet_id = fields.Many2one('acs.claim.sheet', string='Claim Sheet')

    #ACS: Hook method to avoid error of spit invocie on auto invoice.
    def acs_check_auto_spliting_possibility(self, insurance_id):
        return True

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    claim_id = fields.Many2one('hms.insurance.claim', 'Claim')
    insurance_company_id = fields.Many2one('hms.insurance.company', related='claim_id.insurance_company_id', string='Insurance Company', readonly=True)

class Attachments(models.Model):
    _inherit = "ir.attachment"

    patient_id = fields.Many2one('hms.patient', 'Patient')
    claim_id = fields.Many2one('hms.insurance.claim', 'Claim')


class product_template(models.Model):
    _inherit = "product.template"

    hospital_product_type = fields.Selection(selection_add=[('insurance_plan', 'Insurance Plan')])