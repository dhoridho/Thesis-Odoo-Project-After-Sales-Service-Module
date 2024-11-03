# -*- coding: utf-8 -*-
from odoo import _, fields, models, api
from datetime import datetime


class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    def get_account_analytic_tag_data(self):
        query = '''
            SELECT
              aat.id AS account_analytic_id,
              aat.name AS account_analytic
            FROM 
              account_analytic_tag as aat
            WHERE
              aat.name != '' AND aat.active != FALSE
            ORDER BY 
              account_analytic_id desc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.account_analytic_tag_date = datetime.now()
        return result

    def get_dynamic_account_analytic_tag_data(self):
        analytic_tag_datetime = self.env.user.account_analytic_tag_date or datetime.now()
        query = '''
            SELECT
              aat.id AS account_analytic_id,
              aat.name AS account_analytic
            FROM 
              account_analytic_tag as aat
            WHERE
              aat.name != '' AND aat.active != FALSE AND aat.write_date >= '%s' OR aat.create_date >= '%s'
            ORDER BY 
              account_analytic_id desc
        '''%(analytic_tag_datetime, analytic_tag_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.account_analytic_tag_date = datetime.now()
        return result
