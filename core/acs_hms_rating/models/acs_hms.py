#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ACSAppointment(models.Model):
    _name = 'hms.appointment'
    _inherit = ['hms.appointment', 'rating.mixin']

    def appointment_done(self):
        self._send_appointment_rating_mail()
        return super(ACSAppointment, self).appointment_done()

    def _send_appointment_rating_mail(self, force_send=False):
        for rec in self:
            try:
                rating_template = self.sudo().company_id.appointment_rating_mail_template
            except ValueError:
                rating_template = False
            if rating_template:
                rec.rating_send_request(rating_template, lang=rec.patient_id.partner_id.lang, force_send=force_send)

    def _rating_get_parent_field_name(self):
        return 'department_id'

    def rating_get_partner_id(self):
        return self.patient_id.partner_id

    def rating_get_rated_partner_id(self):
        return self.physician_id.partner_id


class HMSPhysician(models.Model):
    _inherit = "hms.physician"

    @api.depends('appointment_ids.rating_ids.rating')
    def _compute_percentage_satisfaction_appointment(self):
        for rec in self:
            activity = rec.appointment_ids.rating_get_grades()
            rec.percentage_satisfaction_appointment = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else -1

    percentage_satisfaction_appointment = fields.Integer(
        compute='_compute_percentage_satisfaction_appointment', string="Happy % on Appointment", store=True, default=-1)

    def action_view_hms_appointment_rating(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_rating.action_view_hms_rating")
        action['name'] = _('Ratings of %s') % (self.name,)
        action['domain'] = [('consumed','=',True), ('res_model','=','hms.appointment'), ('rated_partner_id','=',self.partner_id.id)]
        return action


class HrDepartment(models.Model):
    _inherit = "hr.department"

    @api.depends('appointment_ids.rating_ids.rating')
    def _compute_percentage_satisfaction_appointment(self):
        for rec in self:
            activity = rec.appointment_ids.rating_get_grades()
            rec.percentage_satisfaction_appointment = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else -1

    percentage_satisfaction_appointment = fields.Integer(
        compute='_compute_percentage_satisfaction_appointment', string="Happy % on Appointment", store=True, default=-1)

    def action_view_hms_appointment_rating(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_rating.action_view_hms_rating")
        action['name'] = _('Ratings of %s') % (self.name,)
        action['domain'] = [('consumed','=',True), ('res_model','=','hms.appointment'), ('parent_res_model','=','hr.department'), ('parent_res_id','=',self.id)]
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: