# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime


class ResPartner(models.Model):
    _inherit= "res.partner"

    def get_partner_data(self):
        query = '''
            SELECT
              rp.id AS partner_id,
              rp.display_name AS partner
            FROM 
              res_partner as rp
            WHERE
              rp.name != '' AND rp.active != FALSE
            ORDER BY 
              partner_id desc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.partner_date = datetime.now()
        return result

    def get_dynamic_partner_data(self):
        partner_datetime = self.env.user.partner_date or datetime.now()
        query = '''
            SELECT
              rp.id AS partner_id,
              rp.display_name AS partner
            FROM 
              res_partner as rp
            WHERE
              rp.name != '' AND rp.active != FALSE AND rp.write_date >= '%s' OR rp.create_date >= '%s'
            ORDER BY 
              partner_id desc
        ''' %(partner_datetime, partner_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.partner_date = datetime.now()
        return result