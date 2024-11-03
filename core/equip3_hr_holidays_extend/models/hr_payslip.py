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
        leave_count = self.env['hr.leave.count'].sudo().search([
            ('employee_id', '=', payslip_rec.employee_id.id),
            ('is_expired', '=', True),
            ('expired_date', '>=', date_from),
            ('expired_date', '<=', date_to),
            ('description', 'in', ['Allocation','Extra Leave']),
            ('count', '>', 0),
            ('active', '=', False)])
        if leave_count:
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

    def get_unpaid_leave(self, payslip, date_from, date_to):
        result = {
            "count_leave": 0,
            "count_day": 0,
        }
        payslip_rec = self.sudo().browse(payslip)[0]
        count = 0
        count_day = 0
        leave_count = self.env['hr.leave.count'].sudo().search([
            ('employee_id', '=', payslip_rec.employee_id.id),
            ('is_expired', '=', True),
            ('expired_date', '>=', date_from),
            ('expired_date', '<=', date_to),
            ('description', 'in', ['Leave Allocation Request','Allocation','Extra Leave']),
            ('count', '<', 0),
            ('active', '=', False)])
        if leave_count:
            for rec in leave_count:
                if rec.holiday_status_id.count_on_payslip:
                    if rec.holiday_status_id.rounding == 'rounding_up':
                        counts = math.ceil(rec.count)
                    elif rec.holiday_status_id.rounding == 'rounding_down':
                        counts = math.floor(rec.count)
                    else:
                        counts = rec.count
                else:
                    counts = 0
                count += counts
        result["count_leave"] = abs(count)
        return result

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_worked_day_lines(contracts=contracts,date_from=date_from,date_to=date_to)
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            count = 0
            leave_count = self.env['hr.leave.count'].sudo().search([
                ('employee_id', '=', contract.employee_id.id),
                ('is_expired', '=', True),
                ('expired_date', '>=', date_from),
                ('expired_date', '<=', date_to),
                ('description', 'in', ['Allocation','Extra Leave']),
                ('count', '>', 0),
                ('active', '=', False)])
            if leave_count:
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
            res.append({
                'name': _("Balance Leave"),
                'sequence': 19,
                'code': 'BALANCE_LEAVE',
                'number_of_days': count,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
        return res