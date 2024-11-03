# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from datetime import datetime


class CrmLeadAgeReport(models.Model):
    _name = 'crm.lead.age.report'
    _auto = False

    name = fields.Char(string="Lead Name")
    stage_id = fields.Many2one('crm.stage')
    team_id = fields.Many2one('crm.team', string="Sales Channel")
    partner_id = fields.Many2one('res.partner', string="Customer")
    user_id = fields.Many2one('res.users', string="Sales Person")
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    date_in = fields.Date()
    date_out = fields.Date()
    days = fields.Integer(group_operator = 'sum')
    planned_revenue = fields.Float('Expected Revenue')
    probability = fields.Float('Probability')



    #@api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'crm_lead_age_report')
        self._cr.execute("""
                    CREATE VIEW crm_lead_age_report AS (SELECT
                    p.name as name,
                    q.id as id,
                    q.stage_id as stage_id,
                    p.team_id as team_id,
                    p.partner_id as partner_id,
                    p.user_id as user_id,
                    p.date_deadline as date_deadline,
                    p.expected_revenue as planned_revenue,
                    p.probability as probability,
                    q.date_in as date_in,
                    CASE WHEN q.date_out is not null THEN q.date_out
                           ELSE CURRENT_DATE
                      END AS date_out,
                    CASE WHEN q.date_out is not null THEN q.date_out::date - q.date_in::date  
                    ELSE  CURRENT_DATE::date - q.date_in::date END as days    
                    from crm_lead p 
                    left join lead_age_audit q on (p.id=q.lead_id)
                    left join crm_stage r on (r.id=q.stage_id)
                    WHERE q.date_in is not null and p.type='opportunity' and r.check is not True
                    GROUP BY p.stage_id, q.id, p.name, p.team_id, p.partner_id, p.user_id, 
                    p.date_deadline, p.expected_revenue, p.probability, q.date_in, q.date_out, q.days)
                    """)