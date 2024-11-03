# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ContactsRecruitment(models.Model):
    _name = 'calendar.contacts.recruitment'
    _description = 'Calendar Contacts'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user)
    interviewer = fields.Many2one('res.users', 'Me', required=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('user_id_partner_id_unique', 'UNIQUE(user_id, interviewer)', 'A user cannot have the same contact twice.')
    ]

    @api.model
    def unlink_from_partner_id(self, interviewer):
        return self.search([('interviewer', '=', interviewer)]).unlink()
