# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError
import time
import uuid


class ACSPrescriptionOrder(models.Model):
    _name='prescription.order'
    _description = "Prescription Order"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin', 'acs.qrcode.mixin']
    _order = 'id desc'

    @api.model
    def _current_user_doctor(self):
        physician_id =  False
        ids = self.env['hms.physician'].search([('user_id', '=', self.env.user.id)])
        if ids:
            physician_id = ids[0].id
        return physician_id


    @api.depends('medical_alert_ids')
    def _get_alert_count(self):
        for rec in self:
            rec.alert_count = len(rec.medical_alert_ids)

    READONLY_STATES={'cancel': [('readonly', True)], 'prescription': [('readonly', True)]}

    name = fields.Char(size=256, string='Prescription Number', help='Prescription Number of this prescription', readonly=True, copy=False, tracking=True)
    diseases_ids = fields.Many2many('hms.diseases', 'diseases_prescription_rel', 'diseas_id', 'prescription_id', 
        string='Diseases', states=READONLY_STATES, tracking=True)
    group_id = fields.Many2one('medicament.group', ondelete="set null", string='Medicaments Group', states=READONLY_STATES, copy=False)
    patient_id = fields.Many2one('hms.patient', ondelete="restrict", string='Patient', required=True, states=READONLY_STATES, tracking=True)
    pregnancy_warning = fields.Boolean(string='Pregnancy Warning', states=READONLY_STATES)
    notes = fields.Text(string='Prescription Notes', states=READONLY_STATES)
    prescription_line_ids = fields.One2many('prescription.line', 'prescription_id', string='Prescription line', states=READONLY_STATES)
    company_id = fields.Many2one('res.company', ondelete="cascade", string='Hospital',default=lambda self: self.env.user.company_id, states=READONLY_STATES)
    prescription_date = fields.Datetime(string='Prescription Date', required=True, default=fields.Datetime.now, states=READONLY_STATES, tracking=True, copy=False)
    physician_id = fields.Many2one('hms.physician', ondelete="restrict", string='Prescribing Doctor',
        states=READONLY_STATES, default=_current_user_doctor, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('prescription', 'Prescribed'),
        ('canceled', 'Cancelled')], string='State', default='draft', tracking=True)
    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", 
        string='Appointment', states=READONLY_STATES)
    patient_age = fields.Char(related='patient_id.age', string='Age', store=True, readonly=True)
    treatment_id = fields.Many2one('hms.treatment', 'Treatment', states=READONLY_STATES)
    medical_alert_ids = fields.Many2many('acs.medical.alert', 'prescription_medical_alert_rel','prescription_id', 'alert_id',
        string='Medical Alerts', related="patient_id.medical_alert_ids")
    alert_count = fields.Integer(compute='_get_alert_count', default=0)
    old_prescription_id = fields.Many2one('prescription.order', 'Old Prescription', copy=False, states=READONLY_STATES)

    @api.model
    def create(self, values):
        res = super(ACSPrescriptionOrder, self).create(values)
        res.unique_code = uuid.uuid4()
        return res

    @api.onchange('group_id')
    def on_change_group_id(self):
        product_lines = []
        for rec in self:
            appointment_id = rec.appointment_id and rec.appointment_id.id or False
            for line in rec.group_id.medicament_group_line_ids:
                product_lines.append((0,0,{
                    'product_id': line.product_id.id,
                    'common_dosage_id': line.common_dosage_id and line.common_dosage_id.id or False,
                    'dose': line.dose,
                    'active_component_ids': [(6, 0, [x.id for x in line.product_id.active_component_ids])],
                    'form_id' : line.product_id.form_id.id,
                    'qty_per_day': line.dose,
                    'days': line.days,
                    'short_comment': line.short_comment,
                    'allow_substitution': line.allow_substitution,
                    'appointment_id': appointment_id,
                }))
            rec.prescription_line_ids = product_lines

    @api.onchange('appointment_id')
    def onchange_appointment(self):
        if self.appointment_id and self.appointment_id.treatment_id:
            self.treatment_id = self.appointment_id.treatment_id.id

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_('Prescription Order can be delete only in Draft state.'))
        return super(ACSPrescriptionOrder, self).unlink()

    def button_reset(self):
        self.write({'state': 'draft'})

    def button_confirm(self):
        for app in self:
            if not app.prescription_line_ids:
                raise UserError(_('You cannot confirm a prescription order without any order line.'))

            app.state = 'prescription'
            if not app.name:
                app.name = self.env['ir.sequence'].next_by_code('prescription.order') or '/'

    def print_report(self):
        return self.env.ref('acs_hms.report_hms_prescription_id').report_action(self)

    @api.onchange('patient_id')
    def onchange_patient(self):
        if self.patient_id:
            prescription = self.search([('patient_id', '=', self.patient_id.id),('state','=','prescription')], order='id desc', limit=1)
            self.old_prescription_id = prescription.id if prescription else False

    @api.onchange('pregnancy_warning')
    def onchange_pregnancy_warning(self):
        if self.pregnancy_warning:
            warning = {}
            message = ''
            for line in self.prescription_line_ids:
                if line.product_id.pregnancy_warning:
                    message += _("%s Medicine is not Suggastable for Pregnancy.") % line.product_id.name
                    if line.product_id.pregnancy:
                        message += ' ' + line.product_id.pregnancy + '\n'

            if message:
                return {
                    'warning': {
                        'title': _('Pregnancy Warning'),
                        'message': message,
                    }
                }

    def get_prescription_lines(self):
        appointment_id = self.appointment_id and self.appointment_id.id or False
        product_lines = []
        for line in self.old_prescription_id.prescription_line_ids:
            product_lines.append((0,0,{
                'product_id': line.product_id.id,
                'common_dosage_id': line.common_dosage_id and line.common_dosage_id.id or False,
                'dose': line.dose,
                'active_component_ids': [(6, 0, [x.id for x in line.active_component_ids])],
                'form_id' : line.form_id.id,
                'qty_per_day': line.qty_per_day,
                'days': line.days,
                'short_comment': line.short_comment,
                'allow_substitution': line.allow_substitution,
                'appointment_id': appointment_id,
            }))
        self.prescription_line_ids = product_lines

    def action_prescription_send(self):
        '''
        This function opens a window to compose an email, with the template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('acs_hms', 'acs_prescription_email')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'prescription.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


class ACSPrescriptionLine(models.Model):
    _name = 'prescription.line'
    _description = "Prescription Order Line"

    @api.depends('qty_per_day','days','dose', 'manual_quantity','manual_prescription_qty','state')
    def _get_total_qty(self):
        for rec in self:
            if rec.manual_prescription_qty:
                rec.quantity = rec.manual_quantity
            else:
                rec.quantity = rec.days * rec.qty_per_day * rec.dose

    prescription_id = fields.Many2one('prescription.order', ondelete="cascade", string='Prescription')
    product_id = fields.Many2one('product.product', ondelete="cascade", string='Product', required=True, domain=[('hospital_product_type', '=', 'medicament')])
    allow_substitution = fields.Boolean(string='Allow Substitution')
    prnt = fields.Boolean(string='Print', help='Check this box to print this line of the prescription.',default=True)
    manual_prescription_qty = fields.Boolean(related="product_id.manual_prescription_qty", string="Enter Prescription Qty Manually.", store=True)
    quantity = fields.Float(string='Units', compute="_get_total_qty", inverse='_inverse_total_qty', compute_sudo=True, store=True, help="Number of units of the medicament. Example : 30 capsules of amoxicillin",default=1.0)
    manual_quantity = fields.Float(string='Manual Total Qty')
    active_component_ids = fields.Many2many('active.comp','product_pres_comp_rel','product_id','pres_id','Active Component')
    dose = fields.Float('Dosage', help="Amount of medication (eg, 250 mg) per dose",default=1.0)
    form_id = fields.Many2one('drug.form',related='product_id.form_id', string='Form',help='Drug form, such as tablet or gel')
    route_id = fields.Many2one('drug.route', ondelete="cascade", string='Route', help='Drug form, such as tablet or gel')
    common_dosage_id = fields.Many2one('medicament.dosage', ondelete="cascade", string='Dosage/Frequency', help='Drug form, such as tablet or gel')
    short_comment = fields.Char(string='Comment', help='Short comment on the specific drug')
    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", string='Appointment')
    treatment_id = fields.Many2one('hms.treatment', related='prescription_id.treatment_id', string='Treatment', store=True)
    company_id = fields.Many2one('res.company', ondelete="cascade", string='Hospital', related='prescription_id.company_id')
    qty_available = fields.Float(related='product_id.qty_available', string='Available Qty')
    days = fields.Float("Days",default=1.0)
    qty_per_day = fields.Float(string='Qty Per Day', default=1.0)
    state = fields.Selection(related="prescription_id.state", store=True)

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.active_component_ids = [(6, 0, [x.id for x in self.product_id.active_component_ids])]
            self.form_id = self.product_id.form_id and self.product_id.form_id.id or False,
            self.route_id = self.product_id.route_id and self.product_id.route_id.id or False,
            self.quantity = 1
            self.common_dosage_id = self.product_id.common_dosage_id and self.product_id.common_dosage_id.id or False

            if self.prescription_id and self.prescription_id.pregnancy_warning:
                warning = {}
                message = ''
                if self.product_id.pregnancy_warning:
                    message = _("%s Medicine is not Suggastable for Pregnancy.") % self.product_id.name
                    if self.product_id.pregnancy:
                        message += ' ' + self.product_id.pregnancy
                    warning = {
                        'title': _('Pregnancy Warning'),
                        'message': message,
                    }

                if warning:
                    return {'warning': warning}

    @api.onchange('common_dosage_id')
    def onchange_common_dosage(self):
        if self.common_dosage_id:
            self.qty_per_day = self.common_dosage_id.qty_per_day

    @api.onchange('quantity')
    def _inverse_total_qty(self):
        for line in self:
            if line.product_id.manual_prescription_qty:
                line.manual_quantity = line.quantity
            else:
                line.manual_quantity = 0.0

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: