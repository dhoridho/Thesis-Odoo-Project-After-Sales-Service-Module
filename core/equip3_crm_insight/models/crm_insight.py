# -*- coding: utf-8 -*-
import datetime
import calendar
import pandas as pd
from odoo import models, fields, api
from odoo.tools import date_utils
from odoo.http import request

from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
import logging
_logger = logging.getLogger(__name__)


class CRMLead(models.Model):
    _inherit = 'crm.lead'
    _description = 'CRM Lead'

    crm_manager_id = fields.Many2one("res.users", string="CRM Manager",
                                     store=True)
    monthly_goal = fields.Float(string="Monthly Goal")
    achievement_amount = fields.Float(string="Monthly Achievement")

    @api.model
    def _get_currency(self):
        currency_array = [self.env.user.company_id.currency_id.symbol,
                          self.env.user.company_id.currency_id.position]
        return currency_array

    @api.model
    def check_user_group(self):
        """Checking user group"""
        user = self.env.user
        if user.has_group('sales_team.group_sale_manager'):
            return True
        else:
            return False

    @api.model
    def get_lead_type_data(self):
        last_quarter = self.get_last_quarter()
        closing_month = self.get_monthly_goal()
        revenue = []
        labels = []
        type_id = []
        self._cr.execute('''SELECT crm_lead_type.description AS name, SUM(crm_lead.expected_revenue) AS revenue FROM crm_lead 
            INNER JOIN crm_lead_type ON crm_lead_type.id = crm_lead.type_id 
            INNER JOIN crm_stage ON crm_stage.id = crm_lead.stage_id
            WHERE crm_lead.active='true' AND crm_stage.is_won='true' 
            AND Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE(NOW())) 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW())) 
            GROUP BY crm_lead_type.id ORDER BY crm_lead_type.id DESC
            ''')
        revenue_quarter = self._cr.dictfetchall()
        if revenue_quarter:
            for record in revenue_quarter:
                revenue.append(record.get('revenue'))
                type_id.append(record.get('name'))
            labels.append('This Quarter')

        self._cr.execute('''SELECT crm_lead_type.description AS name, SUM(crm_lead.expected_revenue) AS last_revenue FROM crm_lead 
            INNER JOIN crm_lead_type ON crm_lead_type.id = crm_lead.type_id 
            INNER JOIN crm_stage ON crm_stage.id = crm_lead.stage_id 
            WHERE crm_lead.active='true' AND crm_stage.is_won='true' 
            AND Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE '%s') 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE '%s')
            GROUP BY crm_lead_type.id ORDER BY crm_lead_type.id DESC
            ''' % (last_quarter.strftime('%Y-%m-%d'), last_quarter.strftime('%Y-%m-%d')))
        last_revenue_quarter = self._cr.dictfetchall()
        if last_revenue_quarter:
            for last_record in last_revenue_quarter:
                revenue.append(last_record.get('last_revenue'))
                if not last_record.get('name') in type_id:
                    type_id.append(last_record.get('name'))
            labels.append('Last Quarter')
        final = [revenue, type_id, labels]
        return final

    @api.model
    def get_lost_data(self):
        last_quarter = self.get_last_quarter()
        closing_month = self.get_monthly_goal()
        percent_closing_month = closing_month.get('goals')[5]
        lost = []
        labels = []
        lost_reason = []
        self._cr.execute('''SELECT crm_lost_reason.name AS reason, COUNT(crm_lead.lost_reason) AS lost FROM crm_lead 
            INNER JOIN crm_lost_reason ON crm_lost_reason.id = crm_lead.lost_reason 
            WHERE crm_lead.active='false' AND crm_lead.probability=0 
            AND Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE(NOW())) 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW())) 
            GROUP BY crm_lost_reason.id ORDER BY crm_lost_reason.id DESC
            ''')
        lost_quarter = self._cr.dictfetchall()
        if lost_quarter:
            for record in lost_quarter:
                lost.append(record.get('lost'))
                lost_reason.append(record.get('lost_reason'))
            labels.append('This Quarter')

        self._cr.execute('''SELECT crm_lost_reason.name AS reason, COUNT(crm_lead.lost_reason) AS last_lost FROM crm_lead 
            INNER JOIN crm_lost_reason ON crm_lost_reason.id = crm_lead.lost_reason
            WHERE crm_lead.active='false' AND crm_lead.probability=0 
            AND Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE '%s') 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE '%s')
            GROUP BY crm_lost_reason.id ORDER BY crm_lost_reason.id DESC
            ''' % (last_quarter.strftime('%Y-%m-%d'), last_quarter.strftime('%Y-%m-%d')))
        last_lost_quarter = self._cr.dictfetchall()
        if last_lost_quarter:
            for last_record in last_lost_quarter:
                lost.append(last_record.get('last_lost'))
                if not last_record.get('name') in lost_reason:
                    lost_reason.append(last_record.get('name'))
            labels.append('Last Quarter')
        final = [lost, lost_reason, labels]
        return final

    def get_last_month(self):
        today = fields.Date.today()
        first = today.replace(day=1)
        last_month = first + timedelta(days=-1)
        return last_month

    def get_last_quarter(self):
        today = fields.Date.today()
        up2date = fields.Date.today()
        quarter = pd.Timestamp(today).quarter
        for i in range(4):
            last_day_of_prev_month = up2date.replace(day=1) - timedelta(days=1)
            quarter2 = pd.Timestamp(last_day_of_prev_month).quarter
            if quarter2 == (quarter - 1):
                break
            up2date = last_day_of_prev_month
        last_quarter = last_day_of_prev_month
        return last_quarter

    @api.model
    def get_monthly_goal(self):
        """Monthly Goal Gauge"""
        uid = request.session.uid
        last_month = self.get_last_month()
        last_quarter = self.get_last_quarter()

        currency_symbol = self.env.company.currency_id.symbol

        self._cr.execute('''SELECT SUM(crm_lead.expected_revenue) FROM crm_lead 
        INNER JOIN crm_stage ON crm_stage.id = crm_lead.stage_id 
        WHERE crm_lead.active='true' AND crm_stage.is_won='true' AND Extract(
        MONTH FROM crm_lead.date_closed) = Extract(MONTH FROM DATE(NOW())) AND
        Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
        ''')
        exp_won_data = self._cr.dictfetchall()
        exp_won_data_value = [item['sum'] for item in exp_won_data]
        exp_revenue_this_month = exp_won_data_value[0]
        if exp_revenue_this_month is None:
            exp_revenue_this_month = 0

        self._cr.execute('''SELECT SUM(crm_lead.expected_revenue) FROM crm_lead 
        INNER JOIN crm_stage ON crm_stage.id = crm_lead.stage_id 
        WHERE crm_lead.active='true' AND crm_stage.is_won='true' AND Extract(
        MONTH FROM crm_lead.date_closed) = Extract(MONTH FROM DATE '%s') AND
        Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE '%s')
        ''' % (last_month.strftime('%Y-%m-%d'), last_month.strftime('%Y-%m-%d')))
        last_exp_won_data = self._cr.dictfetchall()
        last_exp_won_data_value = [item['sum'] for item in last_exp_won_data]
        last_month_exp_revenue = last_exp_won_data_value[0]
        if last_month_exp_revenue is None:
            last_month_exp_revenue = 0

        self._cr.execute('''SELECT SUM(crm_lead.expected_revenue) FROM crm_lead 
        INNER JOIN crm_stage ON crm_stage.id = crm_lead.stage_id 
        WHERE crm_lead.active='true' AND crm_stage.is_won='true' AND Extract(
        QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE(NOW())) AND
        Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
        ''')
        exp_revenue_data = self._cr.dictfetchall()
        exp_revenue_data_value = [item['sum'] for item in exp_revenue_data]
        exp_revenue_value_quarter = exp_revenue_data_value[0]
        if exp_revenue_value_quarter is None:
            exp_revenue_value_quarter = 0

        self._cr.execute('''SELECT SUM(crm_lead.expected_revenue) FROM crm_lead 
        INNER JOIN crm_stage ON crm_stage.id = crm_lead.stage_id 
        WHERE crm_lead.active='true' AND crm_stage.is_won='true' AND Extract(
        QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE '%s') AND
        Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE '%s')
        ''' % (last_quarter.strftime('%Y-%m-%d'), last_quarter.strftime('%Y-%m-%d')))
        last_exp_revenue_data = self._cr.dictfetchall()
        last_exp_revenue_data_value = [item['sum'] for item in last_exp_revenue_data]
        last_exp_revenue_value_quarter = last_exp_revenue_data_value[0]
        if last_exp_revenue_value_quarter is None:
            last_exp_revenue_value_quarter = 0

        goals = []
        percent = 0
        if exp_revenue_this_month != 0 and last_month_exp_revenue != 0:
            percent = (exp_revenue_this_month / last_month_exp_revenue * 100) - 100

        percent_quarter = 0
        if exp_revenue_value_quarter != 0 and last_exp_revenue_value_quarter != 0:
            percent_quarter = (exp_revenue_value_quarter / last_exp_revenue_value_quarter * 100) - 100

        goals.append('{:,}'.format(round(exp_revenue_this_month, 2)))
        goals.append(last_month_exp_revenue)
        goals.append(currency_symbol)
        goals.append('{:,}'.format(round(exp_revenue_value_quarter, 2)))
        goals.append(last_exp_revenue_value_quarter)
        goals.append('{:,}'.format(round(percent, 2)))
        goals.append('{:,}'.format(round(percent_quarter, 2)))
        return {'goals': goals}

    @api.model
    def count_generate_account(self):
        generate_account = []
        last_month = self.get_last_month()
        last_quarter = self.get_last_quarter()
        self._cr.execute('''SELECT COUNT(id) FROM res_partner WHERE Extract(MONTH FROM customer_creation_date) 
            = Extract( MONTH FROM DATE(NOW())) AND Extract(Year FROM customer_creation_date) 
            = Extract(Year FROM DATE(NOW()))
            ''')
        record = self._cr.dictfetchall()
        rec_ids = [item['count'] for item in record]
        gen_account = rec_ids[0]
        if gen_account is None:
            gen_account = 0

        self._cr.execute('''SELECT COUNT(id) FROM res_partner WHERE Extract(MONTH FROM customer_creation_date)
            = Extract(MONTH FROM DATE '%s') AND Extract(Year FROM customer_creation_date)
            = Extract(Year FROM DATE '%s')''' % (last_month, last_month))
        last_gen_data = self._cr.dictfetchall()
        last_gen_data_value = [item['count'] for item in last_gen_data]
        last_gen_account = last_gen_data_value[0]
        if last_gen_account is None:
            last_gen_account = 0

        gen_account_this_month = gen_account
        last_month_gen_account = last_gen_account

        percent = 0
        if gen_account_this_month != 0 and last_month_gen_account != 0:
            percent = (gen_account_this_month / last_month_gen_account * 100) - 100

        self._cr.execute('''SELECT COUNT(id) FROM res_partner WHERE Extract(
            QUARTER FROM customer_creation_date) = Extract(QUARTER FROM DATE(NOW())) AND
            Extract(Year FROM customer_creation_date) = Extract(Year FROM DATE(NOW()))
            ''')
        record_quarter = self._cr.dictfetchall()
        rec_ids_quarter = [item['count'] for item in record_quarter]
        gen_account_quarter = rec_ids_quarter[0]
        if gen_account_quarter is None:
            gen_account_quarter = 0

        self._cr.execute('''SELECT COUNT(id) FROM res_partner WHERE Extract(
            QUARTER FROM customer_creation_date) = Extract(QUARTER FROM DATE '%s') AND
            Extract(Year FROM customer_creation_date) = Extract(Year FROM DATE '%s')
            ''' % (last_quarter.strftime('%Y-%m-%d'), last_quarter.strftime('%Y-%m-%d')))
        last_gen_data_quarter = self._cr.dictfetchall()
        last_gen_data_value_quarter = [item['count'] for item in last_gen_data_quarter]
        last_gen_account_quarter = last_gen_data_value_quarter[0]
        if last_gen_account_quarter is None:
            last_gen_account_quarter = 0

        percent_quarter = 0
        if gen_account_quarter != 0 and last_gen_account_quarter != 0:
            percent_quarter = (gen_account_quarter / last_gen_account_quarter * 100) - 100

        generate_account.append(gen_account_this_month)
        generate_account.append(last_month_gen_account)
        generate_account.append(gen_account_quarter)
        generate_account.append(last_gen_account_quarter)
        generate_account.append('{:,}'.format(round(percent, 2)))
        generate_account.append('{:,}'.format(round(percent_quarter, 2)))
        return {'generate_accounts': generate_account}

    @api.model
    def count_opportunities(self):
        opportunity = []
        count_won = self.env['crm.lead'].search_count([('active', '=', True), ('stage_id.is_won', '=', True)])
        count_lost = self.env['crm.lead'].search_count([('active', '=', False), ('probability', '=', 0)])

        opportunity.append(count_won)
        opportunity.append(count_lost)
        return {'opportunity': opportunity}

    @api.model
    def count_won_revenue(self):
        won_revenue = []
        last_month = self.get_last_month()
        last_quarter = self.get_last_quarter()
        self._cr.execute('''SELECT COUNT(id) FROM crm_lead WHERE active='true' 
            AND Extract(MONTH FROM crm_lead.date_closed) = Extract( MONTH FROM DATE(NOW())) 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
            ''')
        record = self._cr.dictfetchall()
        rec_ids = [item['count'] for item in record]
        wonrev = rec_ids[0]
        if wonrev is None:
            wonrev = 0

        self._cr.execute('''SELECT COUNT(id) FROM crm_lead WHERE active='true' 
            AND Extract(MONTH FROM crm_lead.date_closed) = Extract(MONTH FROM DATE '%s') 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE '%s')
            ''' % (last_month, last_month))
        last_wonrev_data = self._cr.dictfetchall()
        last_wonrev_value = [item['count'] for item in last_wonrev_data]
        last_wonrev = last_wonrev_value[0]
        if last_wonrev is None:
            last_wonrev = 0

        won_revenue_this_month = wonrev
        last_month_won_revenue = last_wonrev

        percent = 0
        if won_revenue_this_month != 0 and last_month_won_revenue != 0:
            percent = (won_revenue_this_month / last_month_won_revenue * 100) - 100

        self._cr.execute('''SELECT COUNT(id) FROM crm_lead WHERE active='true'
            AND Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE(NOW())) 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
            ''')
        record_quarter = self._cr.dictfetchall()
        rec_ids_quarter = [item['count'] for item in record_quarter]
        wonrev_quarter = rec_ids_quarter[0]
        if wonrev_quarter is None:
            wonrev_quarter = 0

        self._cr.execute('''SELECT COUNT(id) FROM crm_lead WHERE active='true'
            AND Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE '%s') 
            AND Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE '%s')
            ''' % (last_quarter.strftime('%Y-%m-%d'), last_quarter.strftime('%Y-%m-%d')))
        last_wonrev_data_quarter = self._cr.dictfetchall()
        last_wonrev_value_quarter = [item['count'] for item in last_wonrev_data_quarter]
        last_wonrev_quarter = last_wonrev_value_quarter[0]
        if last_wonrev_quarter is None:
            last_wonrev_quarter = 0

        percent_quarter = 0
        if wonrev_quarter != 0 and last_wonrev_quarter != 0:
            percent_quarter = (wonrev_quarter / last_wonrev_quarter * 100) - 100

        won_revenue.append(won_revenue_this_month)
        won_revenue.append(last_month_won_revenue)
        won_revenue.append(wonrev_quarter)
        won_revenue.append(last_wonrev_quarter)
        won_revenue.append('{:,}'.format(round(percent, 2)))
        won_revenue.append('{:,}'.format(round(percent_quarter, 2)))
        return {'won_revenue': won_revenue}

    @api.model
    def get_trending_data(self):
        trending = []
        self._cr.execute('''SELECT utm_source.name as name, COUNT(crm_lead.source_id) as sources FROM crm_lead 
            INNER JOIN utm_source ON utm_source.id = crm_lead.source_id
            WHERE Extract(MONTH FROM crm_lead.date_closed) = Extract(MONTH FROM DATE(NOW())) AND
            Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
            GROUP BY utm_source.id ORDER BY sources DESC
            ''')
        record_this_month = self._cr.dictfetchall()

        if record_this_month:
            df = pd.DataFrame(record_this_month, columns=['name', 'sources'])
            most_eng_this_month = df.iloc[0]
            least_eng_this_month = df.iloc[-1]

            trending.append(most_eng_this_month['name'])
            trending.append(least_eng_this_month['name'])
        else:
            trending.append('.....')
            trending.append('.....')

        self._cr.execute('''SELECT COUNT(id) FROM res_partner WHERE Extract(
            QUARTER FROM customer_creation_date) = Extract(QUARTER FROM DATE(NOW())) AND
            Extract(Year FROM customer_creation_date) = Extract(Year FROM DATE(NOW()))
            ''')
        record_quarter = self._cr.dictfetchall()
        rec_ids_quarter = [item['count'] for item in record_quarter]
        gen_account_quarter = rec_ids_quarter[0]
        if gen_account_quarter is None:
            gen_account_quarter = 0
        trending.append(gen_account_quarter)

        self._cr.execute('''SELECT utm_source.name as name, COUNT(crm_lead.source_id) as sources FROM crm_lead 
            INNER JOIN utm_source ON utm_source.id = crm_lead.source_id
            WHERE Extract(QUARTER FROM crm_lead.date_closed) = Extract(QUARTER FROM DATE(NOW())) AND
            Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
            GROUP BY utm_source.id ORDER BY sources DESC
            ''')
        record_this_quarter = self._cr.dictfetchall()
        if record_this_quarter:
            df = pd.DataFrame(record_this_quarter, columns=['name', 'sources'])
            fav_this_quarter = df.iloc[0]
            trending.append(fav_this_quarter['name'])
        else:
            trending.append('.....')

        return {'trendings': trending}

    @api.model
    def get_top_source_data(self):
        top_source = []

        self._cr.execute('''SELECT utm_source.name AS name, SUM(crm_lead.expected_revenue) AS sources FROM crm_lead 
            INNER JOIN utm_source ON utm_source.id = crm_lead.source_id
            WHERE Extract(MONTH FROM crm_lead.date_closed) = Extract(MONTH FROM DATE(NOW())) AND
            Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
            GROUP BY utm_source.id ORDER BY sources DESC LIMIT 5
            ''')
        record_this_month = self._cr.dictfetchall()
        if record_this_month:
            for record in record_this_month:
                top_source.append((record.get('name'), int(record.get('sources'))))

        return top_source

    @api.model
    def get_top_team_data(self):
        top_team = []
        team_name = []
        self._cr.execute('''SELECT crm_team.id AS ids, crm_team.name AS name, SUM(crm_lead.expected_revenue) AS sources FROM crm_lead 
            INNER JOIN crm_team ON crm_team.id = crm_lead.team_id
            WHERE Extract(MONTH FROM crm_lead.date_closed) = Extract(MONTH FROM DATE(NOW())) AND
            Extract(Year FROM crm_lead.date_closed) = Extract(Year FROM DATE(NOW()))
            GROUP BY crm_team.id ORDER BY sources DESC, ids ASC LIMIT 5
            ''')
        record_this_month = self._cr.dictfetchall()
        if record_this_month:
            for record in record_this_month:
                top_team.append(int(record.get('sources')))
                team_name.append(record.get('name'))

        final = [team_name, top_team]
        return final
