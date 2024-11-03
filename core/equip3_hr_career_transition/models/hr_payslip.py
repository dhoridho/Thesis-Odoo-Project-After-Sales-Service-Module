# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta
import datetime
import math

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_balance_leave(self, payslip, date_from, date_to):
        result = {
            "count_leave": 0,
            "count_day": 0,
        }
        payslip_rec = self.sudo().browse(payslip)[0]
        count = 0
        count_day = 0

        employee_contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', payslip_rec.employee_id.id),
            ('date_end', '>=', date_from),
            ('date_end', '<=', date_to),
            ('career_transition_id', '!=', False),
            ('state', 'in', ['open','close'])], order='id desc', limit=1)

        leave_count = self.env['hr.leave.count'].sudo().search([
            ('employee_id', '=', payslip_rec.employee_id.id),
            ('is_expired', '=', True),
            ('expired_date', '>=', date_from),
            ('expired_date', '<=', date_to),
            ('description', 'in', ['Allocation','Extra Leave']),
            ('count', '>', 0),
            ('active', '=', False)])

        if employee_contract:
            transition_status = employee_contract.career_transition_id.status
            encashment_leave = employee_contract.career_transition_id.career_transition_type.encashment_leave
            transition_leave_type = employee_contract.career_transition_id.career_transition_type.leave_type_ids
            if transition_status == 'approve' and encashment_leave:
                transition_leave_count = self.env['hr.leave.count'].sudo().search([
                    ('employee_id', '=', payslip_rec.employee_id.id),
                    ('description', 'in', ['Allocation','Extra Leave','Carry Forward']),
                    ('holiday_status_id', 'in', transition_leave_type.ids),
                    ('count', '>', 0),
                    ('active', '=', True)])
                if transition_leave_count:
                    var_count = 0
                    carry_forward = False
                    rounding = False
                    no_of_days = 0
                    carry_based_on_parent = False
                    for rec in transition_leave_count:
                        carry_forward = rec.holiday_status_id.carry_forward
                        rounding = rec.holiday_status_id.rounding
                        no_of_days = rec.holiday_status_id.no_of_days
                        carry_based_on_parent = rec.holiday_status_id.carry_based_on_parent
                        if carry_based_on_parent:
                            var_count += rec.count
                        else:
                            if rec.description == 'Allocation' or rec.description == 'Extra Leave':
                                var_count += rec.count
                            else:
                                var_count += 0
                    if carry_forward == 'remaining_amount':
                        if rounding == 'rounding_up':
                            count = math.ceil(var_count)
                        elif rounding == 'rounding_down':
                            count = math.floor(var_count)
                        else:
                            count = var_count
                    elif carry_forward == 'specific_days' and no_of_days < float(var_count):
                        if rounding == 'rounding_up':
                            count = math.ceil(no_of_days)
                        elif rounding == 'rounding_down':
                            count = math.floor(no_of_days)
                        else:
                            count = no_of_days
                    elif carry_forward == 'specific_days' and no_of_days > float(var_count):
                        if rounding == 'rounding_up':
                            count = math.ceil(var_count)
                        elif rounding == 'rounding_down':
                            count = math.floor(var_count)
                        else:
                            count = var_count
        elif leave_count:
            for rec in leave_count:
                if rec.holiday_status_id.count_on_payslip:
                    if rec.holiday_status_id.carry_forward == 'remaining_amount':
                        if rec.holiday_status_id.rounding == 'rounding_up':
                            counts = math.ceil(rec.count)
                        elif rec.holiday_status_id.rounding == 'rounding_down':
                            counts = math.floor(rec.count)
                        else:
                            counts = rec.count
                    elif rec.holiday_status_id.carry_forward == 'specific_days' and rec.holiday_status_id.no_of_days < float(
                            rec.count):
                        if rec.holiday_status_id.rounding == 'rounding_up':
                            counts = math.ceil(rec.holiday_status_id.no_of_days)
                        elif rec.holiday_status_id.rounding == 'rounding_down':
                            counts = math.floor(rec.holiday_status_id.no_of_days)
                        else:
                            counts = rec.holiday_status_id.no_of_days
                    elif rec.holiday_status_id.carry_forward == 'specific_days' and rec.holiday_status_id.no_of_days > float(
                            rec.count):
                        if rec.holiday_status_id.rounding == 'rounding_up':
                            counts = math.ceil(rec.count)
                        elif rec.holiday_status_id.rounding == 'rounding_down':
                            counts = math.floor(rec.count)
                        else:
                            counts = rec.count
                else:
                    counts = 0
                count += counts
        result["count_leave"] = count
        return result