# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import pytz


class CrmTeam(models.Model):
    _inherit = 'crm.team'


    my_team_id = fields.Many2one('crm.team', string="My Team", compute='_compute_my_team', store=True)

    @api.depends('company_id')
    def _compute_my_team(self):
        for rec in self:
            if rec.id:
                rec.my_team_id = rec.id
            else:
                rec.my_team_id = False