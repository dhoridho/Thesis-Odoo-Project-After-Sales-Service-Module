# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AcsWebcamMixin(models.AbstractModel):
    _name = "acs.webcam.mixin"
    _description = "ACS Webcam Mixin"

    def acs_open_website_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/acs/webcam/' + self._name + '/' + str(self.id),
            'target': 'self',
        }

    acs_webcam_url = fields.Char("Webcam Field")


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner','acs.webcam.mixin']

    def acs_webcam_retrun_action(self):
        self.ensure_one()
        return self.env.ref('base.action_partner_form').id


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = ['res.users','acs.webcam.mixin']

    def acs_webcam_retrun_action(self):
        self.ensure_one()
        return self.env.ref('base.action_res_users').id
