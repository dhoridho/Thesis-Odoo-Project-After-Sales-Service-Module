#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ACSPatient(models.Model):
    _inherit = 'hms.patient'

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.dental_procedure_count = len(rec.dental_procedure_ids)

    dental_procedure_ids = fields.One2many('acs.dental.procedure', 'patient_id', 'Dental Procedures')
    dental_procedure_count = fields.Integer(compute='_rec_count', string='# Dental Procedures')

    def action_view_dental_procedures(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_dental.action_acs_dental_procedure")
        action['domain'] = [('id', 'in', self.dental_procedure_ids.ids)]
        action['context'] = {'default_patient_id': self.id}
        return action


class ACSAppointment(models.Model):
    _inherit = 'hms.appointment'

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    medical_questionnaire_ids = fields.One2many('acs.medical.questionnaire', 'appointment_id', 
        string='Medical Questionnaire', states=READONLY_STATES)
    dental_questionnaire_ids = fields.One2many('acs.dental.questionnaire', 'appointment_id', 
        string='Dental Questionnaire', states=READONLY_STATES)

    @api.model
    def default_get(self, fields):
        res = super(ACSAppointment, self).default_get(fields)
        if self._context.get('is_odontology_appointment'):
            department = self.env['hr.department'].search([('department_type','=','dental')], limit=1)
            if department:
                res['department_id'] = department.id
        return res

    @api.onchange('department_id')
    def onchange_dentaldepartment(self):
        medical_questionnaire_ids = []
        dental_questionnaire_ids = []
        if self.department_id and self.department_id.department_type=='dental':
            questions = self.env['acs.dental.questionnaire.template'].search([])
            for question in questions:
                if question.question_type=='medical':
                    medical_questionnaire_ids.append((0,0,{
                        'name': question.name,
                        'remark': question.remark,
                    }))
                else:
                    dental_questionnaire_ids.append((0,0,{
                        'name': question.name,
                        'remark': question.remark,
                    }))

            self.medical_questionnaire_ids = medical_questionnaire_ids
            self.dental_questionnaire_ids = dental_questionnaire_ids

    def action_view_dental_procedures(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_dental.action_acs_dental_procedure")
        domain = [('appointment_ids', 'in', self.id)]
        if self.treatment_id:
            domain = ['|',('treatment_id', '=', self.treatment_id.id)] + domain
        action['domain'] = domain
        action['context'] = {
            'default_treatment_id': self.treatment_id and self.treatment_id.id or False,
            'default_appointment_ids': [(6,0,[self.id])],
            'default_patient_id': self.patient_id.id,
            'default_physician_id': self.physician_id.id,
        }
        return action

    def create_invoice_line(self, procedure, invoice):
        inv_line_obj = self.env['account.move.line']
        product_id = procedure.product_id
        account_id = product_id.property_account_income_id or product_id.categ_id.property_account_income_categ_id
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                (product_id.name,))

        inv_line_obj.with_context(check_move_validity=False).create({
            'move_id': invoice.id,
            'name': product_id.name,
            'account_id': account_id.id,
            'price_unit': procedure.price_unit,
            'quantity': 1,
            'discount': 0.0,
            'product_uom_id': product_id.uom_id.id,
            'product_id': product_id.id,
            'tax_ids': [(6, 0, product_id.taxes_id and product_id.taxes_id.ids or [])],
        })
        procedure.write({'invoice_id': invoice.id})

    def action_create_dental_invoice(self):
        Moveline = self.env['account.move.line']
        Procedure = self.env['acs.dental.procedure']
        res = super(ACSAppointment, self).create_invoice()

        procedure_ids = Procedure.search([('appointment_ids', 'in', self.id), ('invoice_id','=', False)])
        invoice = self.invoice_id
        if invoice and procedure_ids:
            product_data = []
            for procedure in procedure_ids:
                invoice_lines = self.create_invoice_line(procedure, invoice)
        return res


class HmsTreatment(models.Model):
    _inherit = 'hms.treatment'

    def _rec_count(self):
        rec = super(HmsTreatment, self)._rec_count()
        for rec in self:
            rec.dental_procedure_count = len(rec.dental_procedure_ids)

    dental_procedure_ids = fields.One2many('acs.dental.procedure', 'treatment_id', 'Dental Procedures')
    dental_procedure_count = fields.Integer(compute='_rec_count', string='# Dental Procedures')

    def action_view_dental_procedures(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_dental.action_acs_dental_procedure")
        action['domain'] = [('id', 'in', self.dental_procedure_ids.ids)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_treatment_id': self.id}
        return action

    def action_create_dental_invoice(self):
        procedure_ids = self.dental_procedure_ids.filtered(lambda proc: not proc.invoice_id)
        if not procedure_ids:
            raise UserError(_("There is no Procedure to Invoice or all are already Invoiced."))

        product_data = []
        for procedure in procedure_ids:
            product_data.append({
                'product_id': procedure.product_id,
                'price_unit': procedure.price_unit,
            })
        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
        }
        invoice = self.acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        procedure_ids.write({'invoice_id': invoice.id})

    def view_invoice(self):
        invoices = self.invoice_id + self.dental_procedure_ids.mapped('invoice_id')
        action = self.acs_action_view_invoice(invoices)
        action['context'].update({
            'default_partner_id': self.patient_id.partner_id.id,
            'default_patient_id': self.id,
        })
        return action


class HrDepartment(models.Model): 
    _inherit = "hr.department"

    department_type = fields.Selection(selection_add=[('dental','Odontology')])


class ACSProduct(models.Model):
    _inherit = 'product.template'

    hospital_product_type = fields.Selection(selection_add=[('dental','Dental Process')])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: