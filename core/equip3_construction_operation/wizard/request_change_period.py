from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class RequestChangePeriod(models.TransientModel):
    _name = 'request.change.period'
    _description = 'Request Change Period'

    project_id = fields.Many2one('project.project', string='Project')
    current_start_date = fields.Date(string='Current Start Date', readonly=True)
    current_end_date = fields.Date(string='Current End Date', readonly=True)
    current_duration = fields.Integer(string='Current Duration', compute='_compute_duration')
    planned_start_date = fields.Date(string='Planned Start Date')
    planned_end_date = fields.Date(string='Planned End Date')
    planned_duration = fields.Integer(string='Planned Duration', compute='_compute_duration')
    reason = fields.Text(string='Reason')
    is_date_readonly = fields.Boolean(string='Is Date Readonly')

    @api.depends('planned_end_date')
    def _compute_duration(self):
        for rec in self:
            current_duration = 0
            planned_duration = 0

            if rec.project_id:
                current_duration = (rec.current_end_date - rec.current_start_date).days

            if rec.planned_end_date and rec.planned_start_date:
                planned_duration = (rec.planned_end_date - rec.planned_start_date).days

            rec.planned_duration = planned_duration
            rec.current_duration = current_duration

    # @api.onchange('planned_start_date')
    # def _onchange_planned_start_date(self):
    #     for rec in self:
    #         if rec.project_id.act_start_date:
    #             rec.is_date_readonly = True
    #             rec.planned_start_date = rec.project_id.act_start_date
    #         else:
    #             rec.is_date_readonly = False

    def check_periodical_budget(self):
        for rec in self:
            periodical_budget = rec.env['project.budget'].search([('project_id', '=', rec.project_id.id)])
            # if rec.planned_end_date.month == 12:
            #     next_end_date = rec.planned_end_date + relativedelta(months=+1, day=1, years=+1)
            # else:
            next_end_date = rec.planned_end_date + relativedelta(months=+1, day=1)

            latest_periodical_budget = periodical_budget.filtered(lambda x: x.month.end_date.month ==
                                                                  next_end_date.month and
                                                                  x.month.end_date.year ==
                                                                  next_end_date.year)
            if latest_periodical_budget:
                if latest_periodical_budget.state in ['in_progress', 'complete']:
                    return [False, periodical_budget]
            return [True, periodical_budget]

    def create_period(self, period):
        for rec in self:
            obj_period = period.budget_period_line_ids
            start_date = datetime.strptime(str(period.start_date), "%Y-%m-%d")
            ends_date = datetime.strptime(str(period.end_date), "%Y-%m-%d")
            while start_date.strftime("%Y-%m-%d") <= ends_date.strftime("%Y-%m-%d"):
                end_date = start_date + relativedelta(months=+1, days=-1)
                year_date = start_date.strftime("%Y")
                month_date = start_date.strftime("%B")

                if end_date.strftime("%Y/%m/%d") > ends_date.strftime("%Y/%m/%d"):
                    end_date = ends_date

                if (start_date.date() not in obj_period.mapped('start_date')
                        and end_date.date() not in obj_period.mapped('end_date')):
                    obj_period.create({
                        "year": year_date,
                        "month": month_date,
                        "state": "draft",
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "budget_period_line_id": period.id,
                    })
                start_date = start_date + relativedelta(months=+1)

    def button_confirm(self):
        for rec in self:
            budget_periods = rec.env['project.budget.period'].search([('project', '=', rec.project_id.id), ('start_date', '!=', False), ('end_date', '!=', False), ('state', '!=', 'closed')])
            
            for budget_period in budget_periods:
                budget_period.write({
                    'start_date': rec.planned_start_date,
                    'end_date': rec.planned_end_date,
                })
      
                is_reduce = rec.planned_duration < rec.current_duration
                
                if is_reduce:
                    check_periodical_budget = rec.check_periodical_budget()
                    is_reducible = check_periodical_budget[0]
                    periodical_budget = check_periodical_budget[1]
      
                    if is_reducible:
                        for budget in periodical_budget:
                            if budget.month.end_date.month > rec.planned_end_date.month and \
                                    budget.month.end_date.year >= rec.planned_end_date.year:
                                budget.unlink()
                        for period in budget_period.budget_period_line_ids:
                            if (period.end_date.month > rec.planned_end_date.month and
                                    period.end_date.year >= rec.planned_end_date.year):
                                period.unlink()
                    else:
                        raise ValidationError(_("You can't reduce duration of period that already in progress or complete."))
                else:
                    rec.create_period(budget_period)
                    for period in budget_period.budget_period_line_ids:
                        if (period.end_date.month > rec.planned_end_date.month and
                                period.end_date.year >= rec.planned_end_date.year):
                            period.unlink()

            if rec.is_date_readonly:
                rec.project_id.write({
                    'start_date': rec.planned_start_date,
                    'end_date': rec.planned_end_date,
                    'budget_period_history_ids': [(0, 0, {
                        'project_id': rec.project_id.id,
                        'previous_start_date': rec.current_start_date,
                        'previous_end_date': rec.current_end_date,
                        'previous_duration': rec.current_duration,
                        'planned_start_date': rec.planned_start_date,
                        'planned_end_date': rec.planned_end_date,
                        'planned_duration': rec.planned_duration,
                        'reason': rec.reason,
                    })],
                })
            else:
                rec.project_id.write({
                    'start_date': rec.planned_start_date,
                    'end_date': rec.planned_end_date,
                    'act_start_date': rec.planned_start_date,
                    'budget_period_history_ids': [(0, 0, {
                        'project_id': rec.project_id.id,
                        'previous_start_date': rec.current_start_date,
                        'previous_end_date': rec.current_end_date,
                        'previous_duration': rec.current_duration,
                        'planned_start_date': rec.planned_start_date,
                        'planned_end_date': rec.planned_end_date,
                        'planned_duration': rec.planned_duration,
                        'reason': rec.reason,
                    })],
                })
