# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"
    
    team_id = fields.Many2one('dev.purchase.team', string='Purchase Team')

    def _select(self):
        res = super(PurchaseReport,self)._select()
        return res + """, po.team_id as team_id"""
    
    def _group_by(self):
        res =  super(PurchaseReport,self)._group_by()
        return res + """, po.team_id"""
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: