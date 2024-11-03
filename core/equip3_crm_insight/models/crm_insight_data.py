import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CRMInsightData(models.Model):
    _name = 'crm.insight.data'
    _description = 'CRM Insight Configuration Data'

    name = fields.Char(required=True)
    value = fields.Text(required=True, default="{}")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company.id, required=True)

    @api.constrains('value')
    def _check_value(self):
        for record in self:
            try:
                json.loads(record.value)
            except Exception as err:
                raise ValidationError(str(err))

    _sql_constraints = [
        ('name_company_unique', 'unique (name, company_id)', _('The name of data must be unique per company!'))
    ]
    
    @api.model
    def get_data(self):
        user_tz = self.env.user.tz or 'UTC'

        self._cr.execute('''SELECT
            cl.id,
            cl.active,
            cl.probability,
            cl.date_closed AT TIME ZONE 'UTC' AT TIME ZONE '%s',
            cl.expected_revenue,
            cs.id AS stage_id,
            cs.name AS stage_name,
            cs.is_won AS stage_is_won,
            ct.id AS team_id,
            ct.name AS team_name,
            clt.id AS type_id,
            clt.description AS type_name,
            us.id AS source_id,
            us.name AS source_name,
            clr.id AS reason_id,
            clr.name AS reason_name
        FROM
            crm_lead cl
        LEFT JOIN
            crm_stage cs ON (cs.id = cl.stage_id)
        LEFT JOIN
            crm_team ct ON (ct.id = cl.team_id)
        LEFT JOIN
            crm_lead_type clt ON (clt.id = cl.type_id)
        LEFT JOIN
            utm_source us ON (us.id = cl.source_id)
        LEFT JOIN
            crm_lost_reason clr ON (clr.id = cl.lost_reason)
        ''' % user_tz)

        leads = self._cr.dictfetchall()

        self._cr.execute('''SELECT
            id,
            name,
            customer_creation_date AT TIME ZONE 'UTC' AT TIME ZONE '%s'
        FROM
            res_partner
        ''' % user_tz)

        partners = self._cr.dictfetchall()

        self._cr.execute('''SELECT
            id,
            name,
            value
        FROM 
            crm_insight_data''')

        configs = self._cr.dictfetchall()

        return {
            'leads': leads,
            'partners': partners,
            'configs': configs
        }

