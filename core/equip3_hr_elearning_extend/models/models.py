# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import pytz
import requests
from odoo.exceptions import ValidationError
headers = {'content-type': 'application/json'}


# class equip3_hr_elearning_extend(models.Model):
#     _name = 'equip3_hr_elearning_extend.equip3_hr_elearning_extend'
#     _description = 'equip3_hr_elearning_extend.equip3_hr_elearning_extend'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
class TrainingConduct(models.Model):
    _inherit = 'training.conduct'

    e_learning = fields.Boolean(string="eLearning")
    e_learning_course_id = fields.Many2one('slide.channel')
    website_url = fields.Char('Website URL', help='The full URL to access the document through the website.')
    e_learning_hide = fields.Boolean(string="Hide E-Learning Button", default=False)


    def e_learning_mail(self):
        for rec in self:
            rec.website_url = rec.e_learning_course_id.website_url
            rec.e_learning_hide = True
            for line in rec.conduct_line_ids:
                line.e_learning_mail()
    
    @api.onchange('e_learning')
    def onchange_e_learning(self):
        for rec in self:
            if not rec.e_learning:
                rec.e_learning_course_id = False

class TrainingConductLine(models.Model):
    _inherit = 'training.conduct.line'

    e_learning_progress = fields.Integer(string='E-Learning Progress', compute='_compute_progress')

    @api.depends('employee_id','conduct_id.e_learning_course_id','start_date','end_date')
    def _compute_progress(self):
        for rec in self:
            if rec.conduct_id.e_learning_course_id:
                user_tz = self.env.user.tz
                local_tz = pytz.timezone(user_tz)
                elearning_data = self.env['slide.channel.partner'].sudo().search(
                    [('partner_id', '=', rec.employee_id.user_id.partner_id.id),
                    ('channel_id', '=', rec.conduct_id.e_learning_course_id.id)], limit=1)
                if elearning_data:
                    create_date = datetime.strftime(elearning_data.create_date.astimezone(local_tz), '%Y-%m-%d %H:%M:%S')
                    create_date = datetime.strptime(str(create_date), '%Y-%m-%d %H:%M:%S').date()
                    update_date = datetime.strftime(elearning_data.write_date.astimezone(local_tz), '%Y-%m-%d %H:%M:%S')
                    update_date = datetime.strptime(str(update_date), '%Y-%m-%d %H:%M:%S').date()
                    if not rec.start_date or not rec.end_date:
                        rec.e_learning_progress = 0
                    elif update_date > rec.end_date:
                        if rec.start_date <= create_date <= rec.end_date:
                            rec.e_learning_progress = elearning_data.completion
                        else:
                            rec.e_learning_progress = 0
                    elif update_date <= rec.end_date:
                        if rec.start_date <= update_date <= rec.end_date:
                            rec.e_learning_progress = elearning_data.completion
                        else:
                            rec.e_learning_progress = 0
                    else:
                        rec.e_learning_progress = 0
                else:
                    rec.e_learning_progress = 0
            else:
                rec.e_learning_progress = 0

    def web_get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + "/slides/" + str(
            self.conduct_id.e_learning_course_id.id)
        return url

    def e_learning_mail(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if send_by_wa:
            wa_template = self.env.ref('equip3_hr_elearning_extend.training_invitation_link_wa_template')
            url = self.web_get_url(self)
            if wa_template:
                string_test = str(wa_template.message)
                if "${employee_name}" in string_test:
                    string_test = string_test.replace("${employee_name}", self.employee_id.name)
                if "${course_name}" in string_test:
                    string_test = string_test.replace("${course_name}", self.conduct_id.e_learning_course_id.name)
                if "${url}" in string_test:
                    string_test = string_test.replace("${url}", url)
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                phone_num = str(self.employee_id.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                param = {'body': string_test, 'phone': phone_num}
                domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                try:
                    request_server = requests.post(f'{domain}/sendMessage?token={token}',
                                                   params=param,
                                                   headers=headers, verify=True)
                except ConnectionError:
                    raise ValidationError(
                        "Not connect to API Chat Server. Limit reached or not active")
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.conduct_id:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_training',
                        'email_template_e_learning')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                url = self.web_get_url(self)
                ctx.update({
                    'email_from': self.conduct_id.env.user.email,
                    'email_to': self.employee_id.user_id.email,
                    'url': url,
                })
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                          force_send=True)
            break

class HrJob(models.Model):
    _inherit = 'hr.job'

    e_learning_required_ids = fields.Many2many('slide.channel',string="ELearning Required")