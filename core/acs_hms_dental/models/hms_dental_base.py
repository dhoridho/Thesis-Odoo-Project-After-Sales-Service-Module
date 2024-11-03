# -*- coding: utf-8 -*-

from odoo import api, fields, models ,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AcsDentalQuestionnaireTemplate(models.Model):
    _name="acs.dental.questionnaire.template"
    _description = "Dental Questionnaire Template"

    name = fields.Char(string="Name", required=True)
    remark = fields.Char(string="Remarks")
    question_type = fields.Selection([('medical', 'Medical'),
        ('dental', 'Dental')], default="dental", required=True)


class AcsDentalQuestionnaire(models.Model):
    _name="acs.dental.questionnaire"
    _description = "Dental Questionnaire"

    name = fields.Char(string="Name", required=True)
    is_done = fields.Boolean(string="Y/N", default=False)
    remark = fields.Char(string="Remarks")
    appointment_id = fields.Many2one("hms.appointment", ondelete="cascade", string="Appointment")


class AcsmedicalQuestionnaire(models.Model):
    _name="acs.medical.questionnaire"
    _description = "Medical Questionnaire"

    name = fields.Char(string="Name", required=True)
    is_done = fields.Boolean(string="Y/N", default=False)
    remark = fields.Char(string="Remarks")
    appointment_id = fields.Many2one("hms.appointment", ondelete="cascade", string="Appointment")


class AcsHmsTooth(models.Model):
    _name="acs.hms.tooth"
    _description = "Tooth"
    _order = "sequence"

    name = fields.Char(string="Name", required=True)
    number = fields.Char(string="Number", required=True)
    quadrant = fields.Selection([
        ('upper_right', 'Upper Right'),
        ('upper_left', 'Upper Left'),
        ('lower_right', 'Lower Right'),
        ('lower_left', 'Lower Left')], default="upper_right", required=True)
    sequence = fields.Integer(string="Sequence", default="50")

    def name_get(self):
        result = []
        for rec in self:
            name = rec.number + '. '+ rec.name 
            result.append((rec.id, name))
        return result


class AcsToothSurface(models.Model):
    _name="acs.tooth.surface"
    _description = "Tooth Surface"
    _order = "sequence"

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default="50")
    description = fields.Text(string="Description")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   