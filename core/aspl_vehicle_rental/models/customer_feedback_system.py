# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class AsplCustomerFeedback(models.Model):
    _name = "aspl.customer.feedback"
    _description = "Customer Feedback"

    partner_id = fields.Many2one('res.partner')
    name = fields.Char(related='partner_id.name', string="Name")
    feedback_date = fields.Date(string='Date')
    template_id = fields.Many2one('aspl.feedback.template', string='Template')
    customer_answer_ids = fields.One2many('aspl.customer.feedback.answer', 'customer_feedback_id', string='Answers')


class AsplCustomerFeedbackAnswer(models.Model):
    _name = "aspl.customer.feedback.answer"
    _description = "Customer Feedback Answer"

    customer_feedback_id = fields.Many2one('aspl.customer.feedback', string='Customer Feedback')
    question_id = fields.Many2one('aspl.feedback.question', string='Question')
    template_id = fields.Many2one(related='question_id.template_id', readonly=False)
    answer_ids = fields.Many2many('aspl.feedback.answer', string='Answers')
    none_of_above = fields.Boolean('None of Above')
    comment = fields.Text(string='Comment')
    ratings = fields.Selection([('0', '0'),
                                ('1', '1'),
                                ('2', '2'),
                                ('3', '3'),
                                ('4', '4'),
                                ('5', '5')], string='Rate')


class AsplFeedbackAnswer(models.Model):
    _name = "aspl.feedback.answer"
    _description = "Feedback Answer"

    question_id = fields.Many2one('aspl.feedback.question', string='Questions', required=True)
    answer = fields.Char(string='Answer', size=1024, required=True)


class AsplFeedbackQuestion(models.Model):
    _name = "aspl.feedback.question"
    _description = "Feedback Question"

    name = fields.Char(string='Name', required=True, size=1024)
    comment = fields.Text(string='Comment')
    optional = fields.Boolean('Optional')
    template_id = fields.Many2one('aspl.feedback.template', string='Template')
    question_type = fields.Selection([('normal', 'Normal'),
                                      ('widget', 'Widget')], default='normal', string='Question type')
    answer_mode = fields.Selection([('single', 'Single'),
                                    ('multiple', 'Multiple')], string='Answer mode', default='single')
    add_comment = fields.Boolean('Include Comment')
    answer_ids = fields.One2many('aspl.feedback.answer', 'question_id', string='Answers')
    ratings = fields.Selection([('0', '0'),
                                ('1', '1'),
                                ('2', '2'),
                                ('3', '3'),
                                ('4', '4'),
                                ('5', '5')], string='Rate', readonly=True)
    rate_type = fields.Selection([('star', 'Star'),
                                  ('emoji', 'Emoji')], string="Rate Type", default='star')


class AsplFeedbackTemplate(models.Model):
    _name = "aspl.feedback.template"
    _description = "Feedback Template"

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description', required=True)
    auth_require = fields.Boolean(string='Authentication Require')
    state = fields.Selection(selection=[('draft', 'Draft'), ('open', 'Open'), ('close', 'Close')], string='State',
                             default="draft")
    question_ids = fields.One2many('aspl.feedback.question', 'template_id', string='Questions')
    page_configuration = fields.Selection([('single_page', 'Single Page')], default='single_page', required=True,
                                          string="Website Configuration")
    question_per_page = fields.Integer(string="Questions per Page")
    template_type = fields.Selection([('general', 'General'),
                                      ('rental_order', 'Rental Order')], default='general', string="Template Type")

    def send_mail_to_rental_feedback(self):
        send_mail_after = self.env['ir.config_parameter'].sudo().get_param('aspl_vehicle_rental.send_mail_after')
        number_of_mail = self.env['ir.config_parameter'].sudo().get_param('aspl_vehicle_rental.number_of_email')
        interval = self.env['ir.config_parameter'].sudo().get_param('aspl_vehicle_rental.day_interval')
        IrDefault = self.env['ir.default'].sudo()
        email_template_id = self.env['mail.template'].browse(
            IrDefault.get('res.config.settings', "email_template_id"))
        feedback_template_ids = self.env['aspl.feedback.template'].search([('active', '=', True), ('template_type', '=', 'rental_order')])
        for each_template in feedback_template_ids:
            fleet_order_ids = self.env['fleet.vehicle.order'].search([('state', '=', 'close')])
            for each_order in fleet_order_ids:
                if each_order.return_date:
                    return_date = each_order.return_date.date()
                    for i in range(0, int(number_of_mail)):
                        if return_date == date.today() - relativedelta(days=int(int(send_mail_after) + (i * int(interval)))):
                            if email_template_id:
                                if each_template.template_type == 'rental_order':
                                    url = self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')])
                                    feedback_link = url.value + '/customer_feedback/%s' % each_template.id
                                    email_template_id.email_to = each_order.customer_name.email
                                    email_template_id.body_html = '<p>Dear %s</p><br/>' \
                                                            '<p>We appreciate you giving us the opportunity to serve you. As the ' \
                                                            'service manager of %s, our intention is to always strive for the ' \
                                                            'best possible service. We would be very grateful if you could please take a ' \
                                                            'few minutes to tell us what we have done well and what we could do better.</p><br/>'\
                                                            'Thank you for your business. Our goal is to always meet and exceed your expectations.Sincerely,<br/>'\
                                                            '%s <br/>'\
                                                            '<a href="%s" style="margin-left: 70px;" target="_blank"><button style="cursor: pointer;width: 150px;height: 35px;background-color: #f75960;border: none;padding: 5px;border-radius: 5px;color: #fff;font-weight: bold;">Take the Survey</button></a>' % (each_order.customer_name.name, self.env.user.company_id.name,
                                                                                                        self.env.ref('base.group_erp_manager').users[0].name, feedback_link)
                                    email_template_id.sudo().send_mail(each_template.id, force_send=True)
                            else:
                                raise Warning(_('Please Configure the Mail Template first from Website -> Configuration -> Settings'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
