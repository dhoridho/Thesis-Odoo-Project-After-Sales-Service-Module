# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, _
from odoo.exceptions import UserError

class Employee(models.Model):
    _inherit = 'hr.employee'

    def view_probation(self):
        probation_ids = self.env['employee.probation'].search([('employee_id', '=', self.id)])
        if not probation_ids:
            raise UserError(_('''Probation is not created for '%s' ''') % self.name)

        record_ids = probation_ids.ids
        action = self.env["ir.actions.actions"]._for_xml_id('dev_employee_probation.action_dev_employee_probation')
        if len(record_ids) > 1:
            action['domain'] = [('id', 'in', record_ids)]
        elif len(record_ids) == 1:
            action['views'] = [(self.env.ref('dev_employee_probation.form_dev_employee_probation').id, 'form')]
            action['res_id'] = record_ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: