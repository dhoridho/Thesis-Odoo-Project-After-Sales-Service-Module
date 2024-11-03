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

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_template_id = fields.Many2one('mail.template', string='Email template')
    feedback_template_id = fields.Many2one('aspl.feedback.template', string="Feedback Template")
    send_mail_after = fields.Integer(string='')
    day_interval = fields.Integer(string='Email/Interval')
    number_of_email = fields.Integer(string='Number of Email')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            send_mail_after=int(get_param('aspl_vehicle_rental.send_mail_after')),
            day_interval=int(get_param('aspl_vehicle_rental.day_interval')),
            number_of_email=int(get_param('aspl_vehicle_rental.number_of_email')),
        )
        IrDefault = self.env['ir.default'].sudo()
        feedback_template_id = IrDefault.get('res.config.settings', "feedback_template_id")
        email_template_id = IrDefault.get('res.config.settings', "email_template_id")
        res.update({'feedback_template_id': feedback_template_id or False,
                    'email_template_id': email_template_id or False,})
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', "feedback_template_id", self.feedback_template_id.id)
        IrDefault.set('res.config.settings', "email_template_id", self.email_template_id.id)
        ICPSudo.set_param("aspl_vehicle_rental.send_mail_after", self.send_mail_after)
        ICPSudo.set_param("aspl_vehicle_rental.day_interval", self.day_interval)
        ICPSudo.set_param("aspl_vehicle_rental.number_of_email", self.number_of_email)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
