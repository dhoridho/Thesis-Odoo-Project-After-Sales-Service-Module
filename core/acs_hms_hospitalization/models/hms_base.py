# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class AccountMove(models.Model):
    _inherit = "account.move"

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization',
        help="Enter the patient hospitalization code")

 
class Prescription(models.Model):
    _inherit = 'prescription.order'

    STATES = {'cancel': [('readonly', True)], 'prescription': [('readonly', True)]}

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization',
        help="Enter the patient hospitalization code", states=STATES)
    ward_id = fields.Many2one('hospital.ward',string='Ward/Room No.', ondelete="restrict",
        states=STATES)
    bed_id = fields.Many2one("hospital.bed",string="Bed No.", ondelete="restrict",
        states=STATES)
    print_in_discharge = fields.Boolean('Print In Discharge')
 

class ACSAppointment(models.Model):
    _inherit = 'hms.appointment'

    hospitalization_ids = fields.One2many('acs.hospitalization', 'appointment_id',string='Hospitalizations')

    def action_hospitalization(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.acs_action_form_inpatient")
        action['domain'] = [('appointment_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_appointment_id': self.id}
        return action


class ACSPatient(models.Model):
    _inherit = "hms.patient"
    
    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.hospitalization_count = len(rec.hospitalization_ids)

    hospitalization_ids = fields.One2many('acs.hospitalization', 'patient_id',string='Hospitalizations')
    hospitalization_count = fields.Integer(compute='_rec_count', string='# Hospitalizations')
    death_register_id = fields.Many2one('patient.death.register', string='Death Register')

    hospitalized = fields.Boolean()
    discharged = fields.Boolean()

    @api.onchange('death_register_id')   
    def onchange_death_register(self):
        if self.death_register_id:
            self.date_of_death = self.death_register_id.date_of_death

    def action_hospitalization(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.acs_action_form_inpatient")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {'default_patient_id': self.id}
        return action


class StockMove(models.Model):
    _inherit = "stock.move"
    
    hospitalization_id = fields.Many2one('acs.hospitalization', 'Hospitalization')


class ACSConsumableLine(models.Model):
    _inherit = "hms.consumable.line"

    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization')


class ACSSurgery(models.Model):
    _inherit = "hms.surgery"

    hospital_ot = fields.Many2one('acs.hospital.ot', ondelete="restrict", 
        string='Operation Theater', 
        states={'cancel': [('readonly', True)], 'done': [('readonly', True)]})
    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Hospitalization')


class ACSMedicamentLine(models.Model):
    _inherit = "medicament.line"
    
    hospitalization_id = fields.Many2one('acs.hospitalization', ondelete="restrict", string='Inpatient')


class product_template(models.Model):
    _inherit = "product.template"

    hospital_product_type = fields.Selection(selection_add=[('bed', 'Bed')])


class AcsPatientEvaluation(models.Model):
    _inherit = 'acs.patient.evaluation'

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    hospitalization_id = fields.Many2one('acs.hospitalization', states=READONLY_STATES, string='Hospitalization')


class Physician(models.Model):
    _inherit = "hms.physician"

    def _hos_rec_count(self):
        Hospitalization = self.env['acs.hospitalization']
        for record in self.with_context(active_test=False):
            record.hospitalization_count = Hospitalization.search_count([('physician_id', '=', record.id)])

    hospitalization_count = fields.Integer(compute='_hos_rec_count', string='# Hospitalization')

    def action_hospitalization(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.acs_action_form_inpatient")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action