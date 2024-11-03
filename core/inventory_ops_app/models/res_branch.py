# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime


class ResBranch(models.Model):
    _inherit = "res.branch"

    def get_res_branch_data(self):
        query = ''' 
           SELECT
              rb.id AS branch_id,
              rb.name AS branch
           FROM 
              res_branch as rb
           WHERE
              rb.id != 0
           ORDER BY 
              branch_id asc	
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.res_branch_date = datetime.now()
        return result

    def get_dynamic_res_branch_data(self):
        rb_datetime = self.env.user.res_branch_date or datetime.now()
        query = ''' 
           SELECT
              rb.id AS branch_id,
              rb.name As branch
           FROM 
              res_branch as rb
           WHERE
              rb.id != 0 AND rb.write_date >= '%s' OR rb.create_date >= '%s'
           ORDER BY 
              branch_id asc	
        '''%(rb_datetime, rb_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.res_branch_date = datetime.now()
        return result