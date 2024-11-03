# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta, date
import datetime
from dateutil.relativedelta import relativedelta
import calendar
import plotly
import re


class HrKeyResult(models.Model):
    _name = 'hr.key.result'
    _description = 'HR Key Result'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_member_team(self):
        teams_ids = self.env['hr.teams'].search([]).filtered(lambda line: self.env.user.employee_id.id in line.team_member_ids.ids)
        ids = []
        if teams_ids:
            data_id = [data for data in teams_ids.team_member_ids.ids]
            ids.extend(data_id)
            return [('id','in',ids)]
        else:
            return [('id','=',-1)]

    name = fields.Char('Name', required=True)
    allowed_goal_title_ids = fields.Many2many('hr.goals', string="Allowed Goal Title", compute="_compute_allowed_goal_title")
    goal_title_id = fields.Many2one('hr.goals', string='Goal Title', domain="[('id', 'in', allowed_goal_title_ids)]")
    key_result_type = fields.Selection([('percentage', 'Percentage'), ('kpi_based', 'KPI Based'), ('milestone', 'Milestone')], default='percentage', string='Key Result Type')
    key_result_area_id = fields.Many2one('gamification.goal.definition', string='Key Result Area Id')
    key_result_area = fields.Char('Key Result Area')
    milestone_template_id = fields.Many2one('hr.milestone.temp', string='Milestone Template')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    key_result_target = fields.Float('Key Result Target')
    actual = fields.Float('Actual')
    achievement = fields.Float('Achievement %', compute="compute_achievement", store=True)
    check_in_requency = fields.Selection([('everyday', 'Everyday'),('weekly', 'Weekly'), ('monthly', 'Monthly')], default='everyday', string='Check-In Frequency')
    weekly = fields.Selection([('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'),
                               ('friday', 'Friday'), ('saturday', 'Saturday'), ('sunday', 'Sunday')], default='monday', string='Weekly')
    monthly = fields.Selection([('first_of_month', 'First of Month'), ('last_of_month', 'Last of Month'), ('specific_days', 'Specific Days')], default='first_of_month', string='Monthly')
    priority = fields.Selection([('high', 'High'), ('low', 'Low'), ('medium', 'Medium')], default='high', string='Priority')
    add_member_ids = fields.Many2many('hr.employee', string='Add Member', domain=_get_member_team)
    state = fields.Selection([('pending', 'Pending'), ('on_progress', 'On Progress'), ('done', 'Done'), ('hold', 'Hold'),
                              ('canceled', 'Canceled')], default='pending', string='Status')
    date = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('28', '28'),
        ('29', '29'),
        ('30', '30'),
        ('31', '31')
    ], default='1', string='Date')
    notes = fields.Text('Notes')
    logbook_ids = fields.One2many('hr.key.result.logbook','key_result_id', string="Logbook")
    projection_planning_ids = fields.One2many('hr.key.result.projection.planning','key_result_id', string="Projection Planning")
    source_id = fields.Many2one('hr.key.result', string="Source")
    created_by = fields.Many2one('hr.employee', string="Created by")

    plotly_chart = fields.Text(string='Plotly Chart', compute='_compute_plotly_chart')
    key_result_milestone_ids = fields.One2many('hr.key.result.milestone.area','key_result_id', string="Milestone Area")
    is_childs = fields.Boolean(related="goal_title_id.is_childs", string='Is Childs')


    def _compute_plotly_chart(self):
        for rec in self:
            planning_data_x = []
            planning_data_y = []
            for planning in rec.projection_planning_ids:
                planning_data_x.append(planning.date.strftime('%Y-%m-%d'))
                planning_data_y.append(planning.value)
            planning_data_json = {'x': planning_data_x, 'y': planning_data_y, 'name': 'Planning'}

            actual_data_x = []
            actual_data_y = []
            for actual in rec.logbook_ids:
                pattern = r"Actual: ([\d.]+) -> ([\d.]+)"
                matches = re.findall(pattern, actual.history)
                if matches:
                    actual_data_x.append(actual.timestamp.strftime('%Y-%m-%d'))
                    actual_end = float(matches[0][1])
                    actual_data_y.append(actual_end)
            actual_data_json = {'x': actual_data_x, 'y': actual_data_y, 'name': 'Actual'}

            data = [planning_data_json, actual_data_json]
            rec.plotly_chart = plotly.offline.plot(data, include_plotlyjs=False, output_type='div')


    @api.model
    def create(self, values):
        res = super(HrKeyResult, self).create(values)
        if res.check_in_requency:
            if res.check_in_requency == 'monthly':
                start_date = res.start_date
                ends_date = res.end_date
                days_of_month = []
                last_days_of_month = []
                while start_date < ends_date:
                    days_of_month.append(start_date)
                    last_of_month = calendar.monthrange(start_date.year, start_date.month)[1]
                    last_days_of_month.append(start_date.replace(day=last_of_month))
                    start_date = start_date + relativedelta(months=+1)
                
                projection_planning_list = []
                if res.monthly == 'first_of_month':
                    first_days_of_month = []
                    for day in days_of_month:
                        if day.month == res.start_date.month:
                            if day.day == 1:
                                first_days_of_month.append(day)
                            else:
                                continue
                        else:
                            first_days_of_month.append(day.replace(day=1))
                    count_data = len(first_days_of_month)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in first_days_of_month:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.monthly == 'last_of_month':
                    var_last_days_of_month = []
                    for day in last_days_of_month:
                        if day.month == res.end_date.month:
                            if day.day > res.end_date.day:
                                var_last_days_of_month.append(day.replace(day=int(res.end_date.day)))
                            else:
                                var_last_days_of_month.append(day.replace(day=int(day.day)))
                        else:
                            var_last_days_of_month.append(day)
                    count_data = len(var_last_days_of_month)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in var_last_days_of_month:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.monthly == 'specific_days':
                    specific_days_of_month = []
                    for day in last_days_of_month:
                        if int(res.date) > day.day:
                            specific_date = day.day
                        else:
                            specific_date = int(res.date)

                        if day.month == res.start_date.month:
                            if int(res.date) < int(res.start_date.day):
                                specific_date = int(res.start_date.day)
                            else:
                                specific_date = int(res.date)
                        
                        if day.month == res.end_date.month:
                            if day.day > res.end_date.day:
                                var_last_day = int(res.end_date.day)
                            else:
                                var_last_day = int(day.day)
                            
                            if int(res.date) > var_last_day:
                                specific_date = var_last_day
                            else:
                                specific_date = int(res.date)

                        specific_days_of_month.append(day.replace(day=specific_date))
                    count_data = len(specific_days_of_month)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in specific_days_of_month:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                res.write({'projection_planning_ids': projection_planning_list})
            elif res.check_in_requency == 'weekly':
                delta = res.end_date - res.start_date
                list_of_days = []
                for i in range(delta.days + 1):
                    d = res.start_date + timedelta(i)
                    list_of_days.append(d)
                
                projection_planning_list = []
                if res.weekly == 'monday':
                    monday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'monday':
                            monday_list.append(day)
                    count_data = len(monday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in monday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.weekly == 'tuesday':
                    tuesday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'tuesday':
                            tuesday_list.append(day)
                    count_data = len(tuesday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in tuesday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.weekly == 'wednesday':
                    wednesday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'wednesday':
                            wednesday_list.append(day)
                    count_data = len(wednesday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in wednesday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.weekly == 'thursday':
                    thursday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'thursday':
                            thursday_list.append(day)
                    count_data = len(thursday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in thursday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.weekly == 'friday':
                    friday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'friday':
                            friday_list.append(day)
                    count_data = len(friday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in friday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.weekly == 'saturday':
                    saturday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'saturday':
                            saturday_list.append(day)
                    count_data = len(saturday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in saturday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                elif res.weekly == 'sunday':
                    sunday_list = []
                    for day in list_of_days:
                        name_day = day.strftime("%A")
                        if name_day.lower() == 'sunday':
                            sunday_list.append(day)
                    count_data = len(sunday_list)
                    value = res.key_result_target / count_data
                    next_value = 0
                    for data in sunday_list:
                        projection_planning_list.append([0,0,{
                                                'date': data,
                                                'value': value + next_value
                                                }])
                        next_value += value
                res.write({'projection_planning_ids': projection_planning_list})
            elif res.check_in_requency == 'everyday':
                delta = res.end_date - res.start_date
                list_of_days = []
                for i in range(delta.days + 1):
                    d = res.start_date + timedelta(i)
                    list_of_days.append(d)
                
                projection_planning_list = []
                count_data = len(list_of_days)
                value = res.key_result_target / count_data
                next_value = 0
                for data in list_of_days:
                    projection_planning_list.append([0,0,{
                                            'date': data,
                                            'value': value + next_value
                                            }])
                    next_value += value
                    value += value
                res.write({'projection_planning_ids': projection_planning_list})
        return res
    
    def write(self, vals):
        res = super(HrKeyResult, self).write(vals)
        for rec in self:
            if rec.check_in_requency:
                if rec.check_in_requency == 'monthly':
                    start_date = rec.start_date
                    ends_date = rec.end_date
                    days_of_month = []
                    last_days_of_month = []
                    while start_date < ends_date:
                        days_of_month.append(start_date)
                        last_of_month = calendar.monthrange(start_date.year, start_date.month)[1]
                        last_days_of_month.append(start_date.replace(day=last_of_month))
                        start_date = start_date + relativedelta(months=+1)

                    if rec.monthly == 'first_of_month':
                        first_days_of_month = []
                        for day in days_of_month:
                            if day.month == rec.start_date.month:
                                if day.day == 1:
                                    first_days_of_month.append(day)
                                else:
                                    continue
                            else:
                                first_days_of_month.append(day.replace(day=1))
                        count_data = len(first_days_of_month)
                        value = rec.key_result_target / count_data
                        if first_days_of_month:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in first_days_of_month:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.monthly == 'last_of_month':
                        var_last_days_of_month = []
                        for day in last_days_of_month:
                            if day.month == rec.end_date.month:
                                if day.day > rec.end_date.day:
                                    var_last_days_of_month.append(day.replace(day=int(rec.end_date.day)))
                                else:
                                    var_last_days_of_month.append(day.replace(day=int(day.day)))
                            else:
                                var_last_days_of_month.append(day)
                        count_data = len(var_last_days_of_month)
                        value = rec.key_result_target / count_data
                        if var_last_days_of_month:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in var_last_days_of_month:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.monthly == 'specific_days':
                        specific_days_of_month = []
                        for day in last_days_of_month:
                            if int(rec.date) > day.day:
                                specific_date = day.day
                            else:
                                specific_date = int(rec.date)

                            if day.month == rec.start_date.month:
                                if int(rec.date) < int(rec.start_date.day):
                                    specific_date = int(rec.start_date.day)
                                else:
                                    specific_date = int(rec.date)
                            
                            if day.month == rec.end_date.month:
                                if day.day > rec.end_date.day:
                                    var_last_day = int(rec.end_date.day)
                                else:
                                    var_last_day = int(day.day)
                                
                                if int(rec.date) > var_last_day:
                                    specific_date = var_last_day
                                else:
                                    specific_date = int(rec.date)

                            specific_days_of_month.append(day.replace(day=specific_date))
                        count_data = len(specific_days_of_month)
                        value = rec.key_result_target / count_data
                        if specific_days_of_month:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in specific_days_of_month:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                elif rec.check_in_requency == 'weekly':
                    delta = rec.end_date - rec.start_date
                    list_of_days = []
                    for i in range(delta.days + 1):
                        d = rec.start_date + timedelta(i)
                        list_of_days.append(d)
                    
                    if rec.weekly == 'monday':
                        monday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'monday':
                                monday_list.append(day)
                        count_data = len(monday_list)
                        value = rec.key_result_target / count_data
                        if monday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in monday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.weekly == 'tuesday':
                        tuesday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'tuesday':
                                tuesday_list.append(day)
                        count_data = len(tuesday_list)
                        value = rec.key_result_target / count_data
                        if tuesday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in tuesday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.weekly == 'wednesday':
                        wednesday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'wednesday':
                                wednesday_list.append(day)
                        count_data = len(wednesday_list)
                        value = rec.key_result_target / count_data
                        if wednesday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in wednesday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.weekly == 'thursday':
                        thursday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'thursday':
                                thursday_list.append(day)
                        count_data = len(thursday_list)
                        value = rec.key_result_target / count_data
                        if thursday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in thursday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.weekly == 'friday':
                        friday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'friday':
                                friday_list.append(day)
                        count_data = len(friday_list)
                        value = rec.key_result_target / count_data
                        if friday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in friday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.weekly == 'saturday':
                        saturday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'saturday':
                                saturday_list.append(day)
                        count_data = len(saturday_list)
                        value = rec.key_result_target / count_data
                        if saturday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in saturday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                    elif rec.weekly == 'sunday':
                        sunday_list = []
                        for day in list_of_days:
                            name_day = day.strftime("%A")
                            if name_day.lower() == 'sunday':
                                sunday_list.append(day)
                        count_data = len(sunday_list)
                        value = rec.key_result_target / count_data
                        if sunday_list:
                            rec.projection_planning_ids.unlink()
                        next_value = 0
                        for data in sunday_list:
                            projection_vals = {
                                'key_result_id': rec.id,
                                'date': data,
                                'value': value + next_value,
                            }
                            self.env['hr.key.result.projection.planning'].create(projection_vals)
                            next_value += value
                elif rec.check_in_requency == 'everyday':
                    delta = rec.end_date - rec.start_date
                    list_of_days = []
                    for i in range(delta.days + 1):
                        d = rec.start_date + timedelta(i)
                        list_of_days.append(d)
                    
                    count_data = len(list_of_days)
                    value = rec.key_result_target / count_data
                    if list_of_days:
                        rec.projection_planning_ids.unlink()
                    next_value = 0
                    for data in list_of_days:
                        projection_vals = {
                            'key_result_id': rec.id,
                            'date': data,
                            'value': value + next_value,
                        }
                        self.env['hr.key.result.projection.planning'].create(projection_vals)
                        next_value += value
        return res

    def unlink(self):
        parent_key_result = self.env['hr.key.result'].search([]).filtered(lambda line: self.id == line.source_id.id)
        res = super(HrKeyResult, self).unlink()
        if parent_key_result:
            parent_key_result.unlink()
        return res

    @api.depends()
    def _compute_allowed_goal_title(self):
        for record in self:
            allowed_goals_tittle = self.env['hr.goals'].search([]).filtered(lambda line: self.env.user.id in line.assign_user_ids.ids)
            record.allowed_goal_title_ids = [(6, 0, allowed_goals_tittle.ids)]
    
    @api.depends('key_result_target','actual')
    def compute_achievement(self):
        for rec in self:
            rec.achievement = (rec.actual / rec.key_result_target) * 100 if rec.key_result_target > 0 else 0
    
    @api.onchange('milestone_template_id')
    def onchange_milestone_template(self):
        for rec in self:
            if rec.milestone_template_id:
                rec.key_result_target = sum(rec.milestone_template_id.milestone_line_ids.mapped('weightage'))
                milestone_line = [(5,0,0)]
                for line in rec.milestone_template_id.milestone_line_ids.sorted(key=lambda p: (p.sequence), reverse=False):
                    res = (0, 0, {
                        'sequence': line.sequence,
                        'name': line.id,
                        'weightage': line.weightage,
                    })
                    milestone_line.append(res)
                rec.key_result_milestone_ids = milestone_line

    @api.onchange('key_result_milestone_ids','key_result_milestone_ids.start_date','key_result_milestone_ids.end_date')
    def onchange_key_result_milestone(self):
        for rec in self:
            if rec.key_result_milestone_ids:
                milestone_start_date = rec.key_result_milestone_ids.mapped('start_date')
                milestone_end_date = rec.key_result_milestone_ids.mapped('end_date')
                start_date = []
                for line in milestone_start_date:
                    if isinstance(line, datetime.date):
                        start_date.append(line)
                end_date = []
                for line in milestone_end_date:
                    if isinstance(line, datetime.date):
                        end_date.append(line)
                if start_date:
                    rec.start_date = min(start_date)
                if end_date:
                    rec.end_date = max(end_date)
    
    @api.onchange('actual')
    def onchange_actual(self):
        for rec in self:
            if rec.actual > 0 and rec.actual >= rec.key_result_target:
                rec.state = 'done'
            elif rec.actual > 0 and rec.actual < rec.key_result_target:
                rec.state = 'on_progress'
            elif rec.actual == 0:
                rec.state = 'pending'
    
    def button_checkin(self):
        if self.key_result_type == "milestone":
            milestone_template = self.milestone_template_id.id
        else:
            milestone_template = False
        return {
            'name': "Checkin",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.key.result.checkin.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'default_key_result_id': self.id,
                        'default_goal_title_id': self.goal_title_id.id,
                        'default_milestone_template_id': milestone_template,
                        'default_key_result_target': self.key_result_target,
                        'default_actual': self.actual,
                        'default_achievement': self.achievement,
                        'default_priority': self.priority,
                        'default_state':self.state,
                        },
            'target': 'new',
        }

    def action_projection_planning(self):
        projection_planning = self.env['hr.key.result.projection.planning'].sudo().search([('key_result_id','=',self.id)])
        projection_planning_ids = []
        for data in projection_planning:
            projection_planning_ids.append(data.id)
        if projection_planning_ids:
            value = {
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.key.result.projection.planning',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'name': _('Projection Planning'),
                'domain': [('id', 'in', projection_planning_ids)],
                'target': 'new',
            }
            return value

    @api.onchange('start_date')
    def onchange_start_date(self):
        for rec in self:
            if rec.start_date and not rec.goal_title_id:
                rec.update({'start_date': ''})
                warning = {
                    'title': _('Warning!'),
                    'message': _('please select goal title first!'),
                    }
                return {'warning': warning}
            elif rec.start_date and rec.goal_title_id and not rec.goal_title_id.evaluation_period_id:
                rec.update({'start_date': ''})
                warning = {
                    'title': _('Warning!'),
                    'message': _('please select evaluation period first!'),
                    }
                return {'warning': warning}
            if rec.start_date:
                today = date.today()
                date_start_period = rec.goal_title_id.evaluation_period_id.date_start
                date_end_period = rec.goal_title_id.evaluation_period_id.date_end
                if rec.end_date:
                    if rec.start_date > rec.end_date:
                        rec.update({'start_date': ''})
                        warning = {
                            'title': _('Warning!'),
                            'message': _('start date must be less than start date'),
                            }
                        return {'warning': warning}
                if rec.start_date < date_start_period:
                    rec.update({'start_date': ''})
                    warning = {
                        'title': _('Warning!'),
                        'message': _('start date must be in range evaluation period and greather/same as today'),
                        }
                    return {'warning': warning}
                elif rec.start_date > date_end_period:
                    rec.update({'start_date': ''})
                    warning = {
                        'title': _('Warning!'),
                        'message': _('start date must be in range evaluation period and greather/same as today'),
                        }
                    return {'warning': warning}
    
    @api.onchange('end_date')
    def onchange_end_date(self):
        for rec in self:
            if rec.end_date and not rec.goal_title_id:
                rec.update({'start_date': ''})
                warning = {
                    'title': _('Warning!'),
                    'message': _('please select goal title first!'),
                    }
                return {'warning': warning}
            elif rec.end_date and rec.goal_title_id and not rec.goal_title_id.evaluation_period_id:
                rec.update({'end_date': ''})
                warning = {
                    'title': _('Warning!'),
                    'message': _('please select evaluation period first!'),
                    }
                return {'warning': warning}
            if rec.end_date:
                today = date.today()
                date_start_period = rec.goal_title_id.evaluation_period_id.date_start
                date_end_period = rec.goal_title_id.evaluation_period_id.date_end
                if rec.start_date:
                    if rec.end_date < rec.start_date:
                        rec.update({'end_date': ''})
                        warning = {
                            'title': _('Warning!'),
                            'message': _('end date must be greater than start date'),
                            }
                        return {'warning': warning}
                if rec.end_date < date_start_period:
                    rec.update({'end_date': ''})
                    warning = {
                        'title': _('Warning!'),
                        'message': _('end date must be in range evaluation period and greather/same as today'),
                        }
                    return {'warning': warning}
                elif rec.end_date > date_end_period:
                    rec.update({'end_date': ''})
                    warning = {
                        'title': _('Warning!'),
                        'message': _('end date must be in range evaluation period and greather/same as today'),
                        }
                    return {'warning': warning}

class HrKeyResultLogbook(models.Model):
    _name = 'hr.key.result.logbook'
    _description = 'HR Key Result Logbook'
    _order = "create_date desc"

    key_result_id = fields.Many2one('hr.key.result', string="Key Result Area", ondelete='cascade')
    history = fields.Text('History', readonly=True)
    actual = fields.Float('Actual')
    timestamp = fields.Datetime('Timestamp', readonly=True)
    comment = fields.Text('Comment')
    attachment_file = fields.Binary('Attachment')
    attachment_name = fields.Char('Attachment Name')

class HrKeyResultProjectionPlanning(models.Model):
    _name = 'hr.key.result.projection.planning'
    _description = 'HR Key Result Projection Planning'

    key_result_id = fields.Many2one('hr.key.result', string="Key Result Area", ondelete='cascade')
    date = fields.Date('Date')
    value = fields.Float('Value')
    is_today = fields.Boolean('is Today', compute="_compute_is_today")

    @api.depends('date')
    def _compute_is_today(self):
        for rec in self:
            today = date.today()
            if rec.date < today:
                rec.is_today = False
            else:
                rec.is_today = True

class HrKeyResultMilestoneArea(models.Model):
    _name = 'hr.key.result.milestone.area'
    _description = 'HR Key Result Milestone Area'

    key_result_id = fields.Many2one('hr.key.result', string="Key Result Area", ondelete='cascade')
    sequence = fields.Integer('Sequence')
    name = fields.Many2one('hr.milestone.temp.line', string="Milestone Name")
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    weightage = fields.Float('Weightage')
    actual = fields.Float('Actual')