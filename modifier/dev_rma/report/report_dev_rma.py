# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################

from odoo import models, fields, api

class report_dev_rma(models.AbstractModel): 
    _name = 'report.dev_rma.report_rma_template'
    _description = 'RMA Report'

    def is_replace_product(self,obj):
        for line in obj.rma_lines:
            if line.replace_product_id:
                return True
        return False
            
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['dev.rma.rma'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'dev.rma.rma',
            'docs': docs,
            'is_replace_product':self.is_replace_product,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
