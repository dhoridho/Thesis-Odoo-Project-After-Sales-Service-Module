# coding=utf-8

from odoo import api, fields, models, _, exceptions
from datetime import datetime, date, timedelta
import dateutil.relativedelta
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class Hospitalization(models.Model):
    _name = "acs.hospitalization"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _description = "Patient Hospitalization"
    _order = "id desc"

    @api.model
    def _default_checklist(self):
        vals = []
        checklists = self.env['inpatient.checklist.template'].search([])
        for checklist in checklists:
            vals.append((0, 0, {
                'name': checklist.name,
                'remark': checklist.remark,
            }))
        return vals

    @api.model
    def _default_prewardklist(self):
        vals = []
        prechecklists = self.env['pre.ward.check.list.template'].search([])
        for prechecklist in prechecklists:
            vals.append((0,0,{
                'name': prechecklist.name,
                'remark': prechecklist.remark,
            }))
        return vals

    @api.depends('checklist_ids','checklist_ids.is_done')
    def _compute_checklist_done(self):
        for rec in self:
            if rec.checklist_ids:
                done_checklist = rec.checklist_ids.filtered(lambda s: s.is_done)
                rec.checklist_done = (len(done_checklist)* 100)/len(rec.checklist_ids)
            else:
                rec.checklist_done = 0

    @api.depends('pre_ward_checklist_ids','pre_ward_checklist_ids.is_done')
    def _compute_pre_ward_checklist_done(self):
        for rec in self:
            if rec.pre_ward_checklist_ids:
                done_checklist = rec.pre_ward_checklist_ids.filtered(lambda s: s.is_done)
                rec.pre_ward_checklist_done = (len(done_checklist)* 100)/len(rec.pre_ward_checklist_ids)
            else:
                rec.pre_ward_checklist_done = 0

    def _rec_count(self):
        Invoice = self.env['account.move']
        for rec in self:
            rec.invoice_count = Invoice.sudo().search_count([('hospitalization_id','=',rec.id)])
            rec.prescription_count = len(rec.prescription_ids.ids)
            rec.surgery_count = len(rec.surgery_ids)
            rec.accommodation_count = len(rec.accommodation_history_ids)
            rec.evaluation_count = len(rec.evaluation_ids)

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    name = fields.Char(string='Hospitalization#', copy=False, default="Hospitalization#", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('reserved', 'Reserved'),
        ('hosp','Hospitalized'), 
        ('discharged', 'Discharged'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),], string='Status', default='draft', tracking=True)
    patient_id = fields.Many2one('hms.patient', ondelete="restrict", string='Patient', states=READONLY_STATES, tracking=True)
    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", 
        string='Appointment', states=READONLY_STATES)
    hospitalization_date = fields.Datetime(string='Hospitalization Date', 
        default=fields.Datetime.now, states=READONLY_STATES, tracking=True)
    company_id = fields.Many2one('res.company', ondelete="restrict", 
        string='Hospital', default=lambda self: self.env.user.company_id.id, 
        states=READONLY_STATES)
    department_id = fields.Many2one('hr.department', ondelete="restrict", 
        string='Department', domain=[('patient_department', '=', True)], states=READONLY_STATES)
    attending_physician_ids = fields.Many2many('hms.physician','hosp_pri_att_doc_rel','hosp_id','doc_id',
        string='Primary Doctors', states=READONLY_STATES)
    relative_id = fields.Many2one('res.partner', ondelete="cascade", 
        domain=[('type', '=', 'contact')], string='Patient Relative Name', states=READONLY_STATES)
    relative_number = fields.Char(string='Patient Relative Number', states=READONLY_STATES)
    ward_id = fields.Many2one('hospital.ward', ondelete="restrict", string='Ward/Room', states=READONLY_STATES)
    bed_id = fields.Many2one ('hospital.bed', ondelete="restrict", string='Bed No.', states=READONLY_STATES)
    admission_type = fields.Selection([
        ('routine','Routine'),
        ('elective','Elective'),
        ('urgent','Urgent'),
        ('emergency','Emergency')], string='Admission type', default='routine', states=READONLY_STATES)
    diseas_id = fields.Many2one ('hms.diseases', ondelete="restrict", 
        string='Disease', help="Reason for Admission", states=READONLY_STATES)
    discharge_date = fields.Datetime (string='Discharge date', states=READONLY_STATES, tracking=True)
    no_invoice = fields.Boolean(string='Invoice Exempt', states=READONLY_STATES)
    accommodation_history_ids = fields.One2many("patient.accommodation.history", "hospitalization_id", 
        string="Accommodation History", states=READONLY_STATES)
    accommodation_count = fields.Integer(compute='_rec_count', string='# Accommodation History')
    physician_id = fields.Many2one('hms.physician', string='Primary Physician', states=READONLY_STATES, tracking=True)

    #CheckLists
    checklist_ids = fields.One2many('inpatient.checklist', 'hospitalization_id', 
        string='Admission Checklist', default=lambda self: self._default_checklist(), 
        states=READONLY_STATES)
    checklist_done = fields.Float('Admission Checklist Done', compute='_compute_checklist_done', store=True)
    pre_ward_checklist_ids = fields.One2many('pre.ward.check.list', 'hospitalization_id', 
        string='Pre-Ward Checklist', default=lambda self: self._default_prewardklist(), 
        states=READONLY_STATES)
    pre_ward_checklist_done = fields.Float('Pre-Ward Checklist Done', compute='_compute_pre_ward_checklist_done', store=True)

    #Hospitalization Surgery
    picking_type_id = fields.Many2one('stock.picking.type', ondelete="restrict", 
        string='Picking Type', states=READONLY_STATES)

    consumable_line_ids = fields.One2many('hms.consumable.line', 'hospitalization_id',
        string='Consumable Line', states=READONLY_STATES)

    # Discharge fields
    diagnosis = fields.Text(string="Diagnosis", states=READONLY_STATES)
    clinincal_history = fields.Text(string="Clinical Summary", states=READONLY_STATES)
    examination = fields.Text(string="Examination", states=READONLY_STATES)
    investigation = fields.Text(string="Investigation", states=READONLY_STATES)
    adv_on_dis = fields.Text(string="Advice on Discharge", states=READONLY_STATES)

    discharge_diagnosis = fields.Text(string="Discharge Diagnosis", states=READONLY_STATES)
    op_note = fields.Text(string="Operative Note", states=READONLY_STATES)
    post_operative = fields.Text(string="Post Operative Course", states=READONLY_STATES)
    instructions = fields.Text(string='Instructions', states=READONLY_STATES)

    #Legal Details
    legal_case = fields.Boolean('Legal Case', states=READONLY_STATES)
    medico_legal = fields.Selection([
        ('yes','Yes'),
        ('no','No')], string="If Medico legal", states=READONLY_STATES)
    reported_to_police = fields.Selection([
        ('yes','Yes'),
        ('no','No')], string="Reported to police", states=READONLY_STATES)
    fir_no = fields.Char(string="FIR No.", states=READONLY_STATES, help="Registration number of the police complaint.")
    fir_reason = fields.Char(string="If not reported to police give reason", states=READONLY_STATES)

    #For Basic Care Plan
    nurse_id = fields.Many2one('res.users', ondelete="cascade", string='Primary Nurse', 
        help='Anesthetist data of the patient', states=READONLY_STATES)
    nursing_plan = fields.Text (string='Nursing Plan', states=READONLY_STATES)
    ward_rounds = fields.One2many('ward.rounds', 'hospitalization_id', string='Physician Ward Rounds', states=READONLY_STATES)
    discharge_plan = fields.Text (string='Discharge Plan', states=READONLY_STATES)
    move_ids = fields.One2many('stock.move','hospitalization_id', string='Moves', states=READONLY_STATES)
    invoice_count = fields.Integer(compute='_rec_count', string='# Invoices')
    prescription_ids = fields.One2many('prescription.order', 'hospitalization_id', 'Prescriptions')
    prescription_count = fields.Integer(compute='_rec_count', string='# Prescriptions')
    surgery_ids = fields.One2many('hms.surgery', 'hospitalization_id', "Surgeries")
    surgery_count = fields.Integer(compute='_rec_count', string='# Surgery')
    ref_physician_id = fields.Many2one('res.partner', ondelete='restrict', string='Referring Physician', 
        index=True, help='Referring Physician', states=READONLY_STATES)
    death_register_id = fields.Many2one('patient.death.register', string='Death Register', states=READONLY_STATES)

    evaluation_ids = fields.One2many('acs.patient.evaluation', 'hospitalization_id', '#Evaluations')
    evaluation_count = fields.Integer(compute="_rec_count", string='Evaluations')

    def action_view_evaluation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_acs_patient_evaluation")
        action['domain'] = [('hospitalization_id','=',self.id)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_hospitalization_id': self.id, 'default_physician_id': self.physician_id.id}
        return action

    _sql_constraints = [
        ('name_company_uniq', 'unique (name,company_id)', 'Hospitalization must be unique per company !')
    ]

    @api.model
    def create(self, values):
        patient_id = values.get('patient_id')
        active_hospitalizations = self.search([('patient_id','=',patient_id),('state','not in',['cancel','done','discharged'])])
        if active_hospitalizations:
            raise ValidationError(_("Patient Hospitalization is already active at the moment. Please complete it before creating new."))
        if values.get('name', 'Hospitalization#') == 'Hospitalization#':
            values['name'] = self.env['ir.sequence'].next_by_code('acs.hospitalization') or 'Hospitalization#'
        return super(Hospitalization, self).create(values)

    def action_confirm(self):
        self.state = 'confirm'

    def action_reserve(self):
        History = self.env['patient.accommodation.history']
        for rec in self:
            rec.bed_id.sudo().write({'state': 'reserved'})
            rec.state = 'reserved'
            History.sudo().create({
                'hospitalization_id': rec.id,
                'patient_id': rec.patient_id.id,
                'ward_id': self.ward_id.id,
                'bed_id': self.bed_id.id,
                'start_date': datetime.now(),
            })

    def action_hospitalize(self):
        History = self.env['patient.accommodation.history']
        for rec in self:
            rec.bed_id.sudo().write({'state': 'occupied'})
            rec.state = 'hosp'
            rec.patient_id.write({'hospitalized': True})

    def action_discharge(self):
        for rec in self:
            rec.bed_id.sudo().write({'state': 'free'})
            rec.state = 'discharged'
            rec.discharge_date = datetime.now()
            for history in rec.accommodation_history_ids:
                if rec.bed_id == history.bed_id:
                    history.end_date = datetime.now()
            rec.patient_id.write({'discharged': True})

    def action_done(self):
        self.state = 'done'
        self.consume_hopitalization_material()
        if not self.discharge_date:
            self.discharge_date = datetime.now()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            rec.bed_id.sudo().write({'state': 'free'}) 

    def action_draft(self):
        self.state = 'draft'

    def action_prescription(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('hospitalization_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.patient_id.id,
            'default_physician_id':self.physician_id.id,
            'default_hospitalization_id': self.id,
            'default_ward_id': self.ward_id.id,
            'default_bed_id': self.bed_id.id}
        return action

    def action_accommodation_history(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_hospitalization.action_accommodation_history")
        action['domain'] = [('hospitalization_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.patient_id.id,
            'default_hospitalization_id': self.id}
        return action

    def action_view_surgery(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_surgery.act_open_action_form_surgery")
        action['domain'] = [('hospitalization_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.patient_id.id,
            'default_hospitalization_id': self.id}
        return action

    def view_invoice(self):
        invoices = self.env['account.move'].search([('hospitalization_id', '=', self.id)])
        action = self.acs_action_view_invoice(invoices)
        return action

    def consume_hopitalization_material(self):
        for rec in self:
            if not rec.company_id.hospitalization_usage_location:
                raise UserError(_('Please define a location where the consumables will be used during the surgery in company.'))
            if not rec.company_id.hospitalization_stock_location:
                raise UserError(_('Please define a hospitalization location from where the consumables will be taken.'))
 
            dest_location_id  = rec.company_id.hospitalization_usage_location.id
            source_location_id  = rec.company_id.hospitalization_stock_location.id
            for line in rec.consumable_line_ids.filtered(lambda s: not s.move_id):
                move = self.consume_material(source_location_id, dest_location_id,
                    {
                        'product': line.product_id,
                        'qty': line.qty,
                    })
                move.hospitalization_id = rec.id
                line.move_id = move.id

    def get_hospitalizaion_invoice_data(self):
        product_data = []
        if self.surgery_ids:
            surgery_ids = self.surgery_ids.filtered(lambda s: not s.invoice_id)
            if surgery_ids:
                surgery_data = surgery_ids.get_surgery_invoice_data()
                product_data += surgery_data

        if self.accommodation_history_ids:
            product_data.append({
                'name': _("Accommodation Charges"),
            })
            for bed_history in self.accommodation_history_ids:
                product_data.append({
                    'product_id': bed_history.bed_id.product_id,
                    'quantity': bed_history.rest_time,
                })

        if self.consumable_line_ids:
            product_data.append({
                'name': _("Consumed Product Charges"),
            })
            for list_consumable in self.consumable_line_ids:
                product_data.append({
                    'product_id': list_consumable.product_id,
                    'quantity': list_consumable.qty,
                })
        return product_data

    def action_create_invoice(self):
        product_data = []
        for hospitalization in self:
            hosp_product_data = hospitalization.get_hospitalizaion_invoice_data()
            product_data += hosp_product_data
            
        inv_data = {
            'ref_physician_id': self.ref_physician_id and self.ref_physician_id.id or False,
            'physician_id': self.physician_id and self.physician_id.id or False,
        }
        invoice_id = self.acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        invoice_id.write({
            #'create_stock_moves': False,
            'hospitalization_id': self.id,
        })

        surgery_ids = self.mapped('surgery_ids').filtered(lambda s: not s.invoice_id)
        if surgery_ids:
            surgery_ids.write({'invoice_id': invoice_id.id})
        return invoice_id

    def button_indoor_medication(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('hospitalization_id', '=', self.id)]
        action['views'] = [(self.env.ref('acs_hms.view_hms_prescription_order_form').id, 'form')]
        action['context'] = {
            'default_patient_id': self.patient_id.id,
            'default_physician_id':self.physician_id.id,
            'default_hospitalization_id': self.id,
            'default_ward_id': self.ward_id.id,
            'default_bed_id': self.bed_id.id}
        return action
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: