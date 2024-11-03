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
from datetime import date


class Review(models.Model):
    _name = 'probation.review'
    _description = 'Review of Probation'

    def approve_review(self):
        self.approved_by_hr = True

    probation_id = fields.Many2one('employee.probation', string='Probation')
    review_date = fields.Date(string='Date', default=date.today(), readonly=True)
    user_id = fields.Many2one('res.users', string="Reviewer", default=lambda self: self.env.user, readonly=True)
    short_review = fields.Char(string='Short Review')
    performance = fields.Selection(selection=[('excellent', 'Excellent'),
                                              ('good', 'Good'),
                                              ('average', 'Average'),
                                              ('poor', 'Poor'),
                                              ('worst', 'Worst'),
                                              ], default='average', required=True, string='Performance')
    rating = fields.Selection(selection=[('1', 'One'),
                                         ('2', 'Two'),
                                         ('3', 'Tree'),
                                         ('4', 'Four'),
                                         ('5', 'Five'),
                                         ('6', 'Six'),
                                         ], string='Rating')
    description = fields.Text(string='Description')
    approved_by_hr = fields.Boolean(string='Approved by HR', copy=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: