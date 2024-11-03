# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import fields, models, api, _


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def get_warehouse_expiry_detail(self, company_id):
        quant_sql = '''
            SELECT 
                sq.location_id as location_id, 
                sum(sq.quantity) as expire_count, 
                sw.name as warehouse_name
            FROM 
                stock_warehouse sw
                LEFT JOIN stock_location sl on sl.id = sw.lot_stock_id
                LEFT JOIN stock_quant sq on sq.location_id = sl.id
            WHERE 
                sq.state_check = 'Near Expired'
                AND sw.company_id = %s
            GROUP BY 
                sq.location_id,sw.name;
                ''' % (company_id)
        self._cr.execute(quant_sql)
        warehouse_near_expire = self._cr.dictfetchall()
        return warehouse_near_expire

    def get_location_detail(self, company_id):
        quant_sql = '''
            SELECT 
                sq.location_id as location_id, 
                sum(sq.quantity) as expire_count , 
                sl.complete_name as location_name
            FROM 
                stock_quant sq
                LEFT JOIN stock_location sl on sl.id = sq.location_id
            WHERE 
                sl.usage = 'internal' AND 
                sl.company_id = %s AND 
                sl.active = True AND 
                sq.state_check = 'Near Expired'
            GROUP BY 
                sq.location_id,sl.complete_name
                ''' % (company_id)
        self._cr.execute(quant_sql)
        location_near_expire = self._cr.dictfetchall()
        return location_near_expire

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: