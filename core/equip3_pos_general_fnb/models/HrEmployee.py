# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime


class PosBranch(models.Model):
    _inherit = "hr.employee"
    
    remaining_budget = fields.Float(string="Remaining Budget", compute="_compute_remaining_budget")

    def _compute_remaining_budget(self):
        limit_budget = 0
        pos_config_id = self._context.get('pos_config_id')
        if pos_config_id:
            pos_config = self.env['pos.config'].sudo().browse([pos_config_id])
            if pos_config:
                limit_budget = pos_config.employee_meal_limit_budget

        for employee in self:
            remaining_budget = limit_budget
            if pos_config_id:
                today_date = str(datetime.now().strftime('%Y-%m-%d'))
                domain = [('employee_id','=',employee.id), ('config_id','=',pos_config_id)]
                domain += [('order_date','>=', today_date + ' 00:00:00'), ('order_date','<=', today_date + ' 23:59:59')]
                employee_meals = self.env['pos.employee.meal.history'].search_read(domain, ['order_date','order_value'])
                used_budget = sum([x['order_value'] for x in employee_meals])

                remaining_budget = remaining_budget - used_budget
                
            employee.remaining_budget = remaining_budget