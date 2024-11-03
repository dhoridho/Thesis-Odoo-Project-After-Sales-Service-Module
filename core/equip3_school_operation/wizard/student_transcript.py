from email.policy import default
from odoo import fields, models, api, _, tools
from odoo.exceptions import UserError, ValidationError
import base64


class StudentTranscriptWizard(models.TransientModel):
    _name = "academic.tracking.transcript"

    def get_student_id(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            return self.env["academic.tracking"].browse(active_ids[0])
        return self.env["academic.tracking"]

    student = fields.Many2one(comodel_name='academic.tracking', string='Student', default=get_student_id, readonly="1")
    program = fields.Many2one(comodel_name='standard.standard', string='Program')
    intake = fields.Many2one(comodel_name='school.standard', string='Intake')
    academic_year = fields.Many2one(comodel_name='academic.year', string='Academic Year')
    print_all = fields.Boolean(string='Print All', default=True)
    term = fields.Many2many(comodel_name='academic.month', string='Term')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.onchange('student')
    def _filter_program(self):
        for rec in self:
            dom = {'domain': {'program': [('id', 'in', rec.student.program_id.ids)]}}
        return dom

    @api.onchange('student')
    def _filter_intake(self):
        for rec in self:
            dom = {'domain': {'intake': [('id', 'in', rec.student.program_id.intake_ids.ids)]}}
        return dom

    @api.onchange('student')
    def _filter_academic_year(self):
        for rec in self:
            dom = {'domain': {'academic_year': [('id', 'in', rec.student.all_score_subject_ids.year_id.ids)]}}
        return dom

    @api.onchange('academic_year')
    def _filter_term(self):
        for rec in self:
            rec.term = False
            dom = {'domain': {'term': [('id', 'in', rec.student.all_score_subject_ids.filtered(
                lambda x: x.year_id == rec.academic_year).term_id.ids)]}}
        return dom

    def prepare_data_to_print(self):
        tracking_id = self.student
        if self.print_all:
            ems_subject_ids = tracking_id.all_score_subject_ids.sudo().filtered(lambda x: x.intake_id == self.intake)
        else:
            ems_subject_ids = self.env['subject.weightage'].sudo().search(
                [('all_academic_tracking_id', '=', tracking_id.id), ('intake_id', '=', self.intake.id),
                 ('year_id', '=', self.academic_year.id), ('term_id', 'in', self.term.ids)])
        data = {}
        for ems_subject_id in ems_subject_ids:
            try_key = '%s%s' % (ems_subject_id.year_id.id, ems_subject_id.term_id.id)
            subject_id = ems_subject_id.subject_id
            if try_key in data:
                data[try_key]['line_ids'].append(
                    [subject_id.code, subject_id.name, ems_subject_id.credits, ems_subject_id.grade.grade])
            else:
                data[try_key] = {
                    'year_id': ems_subject_id.year_id.name,
                    'term_id': ems_subject_id.term_id.name,
                    'line_ids': [
                        [subject_id.code, subject_id.name, ems_subject_id.credits, ems_subject_id.grade.grade or '']]
                }
        return data

    def button_print_transcript(self, partner_id=False):
        data = self.get_report_data()
        return self.env.ref('equip3_school_operation.wizard_student_transcript').report_action(self, data=data)

    def get_address_details(self, partner):
        return self._get_address_details(partner)

    def get_street(self, partner):
        return self._get_street(partner)

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False
    
    def get_report_data(self):
        dummy = self.read()[0]
        academic_tracking_student = self.env['academic.tracking'].search([('id', '=', dummy['student'][0])]).student_id
        partner_id = self.env.company.partner_id
        data = {
            'tracking_id': self.read()[0],
            'student_id': self.env['student.student'].search([('id', '=', academic_tracking_student.id)]).pid,
            'data': self.prepare_data_to_print(),
            'company': self.env.company.read()[0],
            'address': self._get_address_details(partner_id),
            'street': self._get_street(partner_id),
            'font_family': self.env.company.font_id.family,
            'font_size': self.env.company.font_size,
            'mobile': partner_id.mobile,
            'email': partner_id.email,
            'partner': partner_id.name,
        }

        return data
    
    def print_and_send_email(self):
        data = self.get_report_data()
        transcript_pdf = self.env.ref("equip3_school_operation.wizard_student_transcript").sudo()._render_qweb_pdf(self.id, data=data)
        attachment = self.env['ir.attachment'].create({
            'name': "Student Transcript.pdf",
            'type': 'binary',
            'datas': base64.b64encode(transcript_pdf[0]).decode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        }) 
        email_template = self.env.ref("equip3_school_operation.academic_transcript_email_template")
        email_template.attachment_ids = [(6, 0, [attachment.id])]
        email_template.send_mail(self.id, force_send=True)
