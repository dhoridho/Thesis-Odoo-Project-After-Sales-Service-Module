# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosEmployeeMealHistory(models.TransientModel):
    _name = 'pos.employee.meal.history'
    _description = 'Pos Employee Meal History'
    _rec_name = 'employee_id'
    _order = 'order_date desc'

    order_date = fields.Datetime('Order Date')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    order_id = fields.Many2one('pos.order', string='Order ID')
    order_value = fields.Float(string='Order Value')
    cashier_id = fields.Many2one('res.users', string='Cashier') 
    config_id = fields.Many2one('pos.config', string='POS Config') 
    session_id = fields.Many2one('pos.session', string='POS Session') 
    company_id = fields.Many2one('res.company','Company',related="session_id.company_id")
    branch_id = fields.Many2one('res.branch','Branch',related="session_id.pos_branch_id")

