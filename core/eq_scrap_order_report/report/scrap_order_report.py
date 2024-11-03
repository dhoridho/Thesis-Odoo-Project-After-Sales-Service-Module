# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import models, fields, api


class eq_scrap_order_report_scrap_order_report(models.AbstractModel):
    _name = 'report.eq_scrap_order_report.scrap_order_report'
    _description = 'Report Scrap Order Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('eq_scrap_order_report.scrap_order_report')
        record_id = data['form']['id'] if data and data['form'] and data['form']['id'] else docids[0]
        records = self.env['wizard.scrap.order.report'].browse(record_id)
        return {
           'doc_model': report.model,
           'docs': records,
           'data': data
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: