# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OpportunityDetailsInherit(models.Model):
    _inherit = 'crm.lead'

    construction_type = fields.Selection([('construction','Construction'),('engineering','Engineering')], string="Construction Type", default='construction', required=True)
    
    # def _prepare_vals(self, record, list_project, project, short_name, customer, salesperson, team, director):
    #     return {
    #         'name': project,
    #         'project_short_name': short_name,
    #         'project_scope_line_ids': list_project,
    #         'partner_id': customer,
    #         'sales_person' : salesperson,
    #         'sales_team' : team,
    #         'project_director': director,
    #         'department_type': 'project',
    #         'lead_id': record.id,
    #         'notification_claim': [(6, 0, [user.id for user in self.env.user])],
    #         'construction_type': record.construction_type,
    #     }
    
    def _prepare_vals(self, record, list_project, project, short_name, customer, salesperson, team, director, branch):
        res = super(OpportunityDetailsInherit, self)._prepare_vals(record, list_project, project, short_name, customer, salesperson, team, director, branch)
        res['construction_type'] = record.construction_type

        return res

    