# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import json

class ResPartner(models.Model):
    _inherit = 'res.partner'

    salesperson_ids = fields.Many2many('res.users', 'res_users_rel', string='Salespersons')
    lead_sequence = fields.Char(string="Leads ID", readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company, readonly=True)
    filter_team_id = fields.Char(string="Filter Sales Team",compute='_compute_filter_team_id', store=False)

    @api.depends('user_id')
    def _compute_filter_team_id(self):
        for rec in self:
            my_team_ids = []
            if rec.user_id:
                my_team_ids.extend(self.env['crm.team'].search(['|','|',('user_id', '=', rec.user_id.id),('additional_leader_ids', 'in', rec.user_id.id),('member_ids', 'in', rec.user_id.id)]).ids)
                # my_team_ids.append(rec.user_id.sale_team_id.id)
                # my_team_ids.extend(rec.user_id.my_team_ids.ids)
                rec.filter_team_id = json.dumps([('id', 'in', my_team_ids)])
                rec.team_id = my_team_ids[0]
            else:
                rec.filter_team_id = json.dumps([])
                rec.team_id = False

    @api.model
    def create(self, values):
        self.env.context = dict(self.env.context)
        if 'is_leads' in values:
            if values.get('is_leads', False):
                sequence = self.env['ir.sequence'].next_by_code('res.partner.lead.sequence')
                values.update({
                    'lead_sequence': sequence,
                    'is_customer': False,
                    'customer_rank': 0,
                    'customer_sequence': None,
                })
        if 'is_company' in values and 'create_company' in self.env.context:
            values['company_id'] = False
        res = super(ResPartner, self).create(values)
        if 'create_company' in self.env.context:
            self.env.context.update({
                'partner_id': res.id,
            })
        return res

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def create(self, values):
        self.env.context = dict(self.env.context)
        self.env.context.update({
            'create_company': True,
        })
        res = super(ResCompany, self).create(values)
        if 'partner_id' in self.env.context:
            partner_id = self.env['res.partner'].browse(self.env.context.get('partner_id'))
            if partner_id:
                partner_id.company_id = res.id
        return res

