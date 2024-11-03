from odoo import api,fields,models
from lxml import etree
from odoo.exceptions import ValidationError


class Equip3OvertimeRules(models.Model):
    _name = 'overtime.rules'
    _rec_name = 'name'
    name = fields.Char(required=1)
    code = fields.Char(required=1)
    minimum_time = fields.Integer(required=1)
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company)
    works_day = fields.One2many('overtime.work.days.line','overtime_id')
    off_days_working = fields.One2many('overtime.off.time.days','overtime_id')
    off_days_working_per_week = fields.One2many('overtime.off.time.days.week','overtime_id')
    off_days_public_holiday = fields.One2many('overtime.off.public.holiday','overtime_id')
    meal_allowance_work_days = fields.One2many('meal.allowance.work.days','overtime_rules_id')
    meal_allowance_offtime_five_days = fields.One2many('meal.allowance.offtime.five.days','overtime_rules_id')
    meal_allowance_offtime_six_days = fields.One2many('meal.allowance.offtime.six.days','overtime_rules_id')
    meal_allowance_off_public_holiday = fields.One2many('meal.allowance.off.public.holiday','overtime_rules_id')
    break_time_work_days = fields.One2many('break.time.work.days','overtime_rules_id')
    break_time_offtime_five_days = fields.One2many('break.time.offtime.five.days','overtime_rules_id')
    break_time_offtime_six_days = fields.One2many('break.time.offtime.six.days','overtime_rules_id')
    break_time_off_public_holiday = fields.One2many('break.time.off.public.holiday','overtime_rules_id')
    overtime_rounding_ids = fields.One2many('overtime.rounding', 'overtime_rules_id')
    is_use_ovt_limit = fields.Boolean('Use Overtimes Limitation')
    ovt_limit_day = fields.Float('Limit in a Day', default=4)
    ovt_limit_week = fields.Float('Limit in a Week', default=18)
    use_government_rule = fields.Boolean('Use Goverment Rule', default=True)
    rules_line_ids = fields.One2many('overtime.rules.line','overtime_rules_id')
    break_overtime_rules_line_ids = fields.One2many('break.overtime.rules.line','overtime_rules_id')
    meal_allowance_rules_line_ids = fields.One2many('meal.allowance.overtime.rules.line','overtime_rules_id')
    off_days_five_ids = fields.One2many('overtime.off.five.rules.line','overtime_rules_id')
    off_days_six_ids = fields.One2many('overtime.off.six.rules.line','overtime_rules_id')
    off_days_public_ids = fields.One2many('overtime.off.public.rules.line','overtime_rules_id')
    break_off_five_ids = fields.One2many('break.off.five.rules.line','overtime_rules_id')
    break_off_six_ids = fields.One2many('break.off.six.rules.line','overtime_rules_id')
    break_off_public_ids = fields.One2many('break.off.public.rules.line','overtime_rules_id')
    meal_allowance_off_five_ids = fields.One2many('meal.allowance.off.five.rules.line','overtime_rules_id')
    meal_allowance_off_six_ids = fields.One2many('meal.allowance.off.six.rules.line','overtime_rules_id')
    meal_allowance_off_public_ids = fields.One2many('meal.allowance.off.public.rules.line','overtime_rules_id')
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3OvertimeRules, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3OvertimeRules, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Equip3OvertimeRules, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_all_approver'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.constrains('rules_line_ids')
    def _check_rules_line_ids(self):
        for record in self:
            if len(record.rules_line_ids) > 1:
                raise ValidationError("Work Days can't add more than 1 lines")

    @api.constrains('off_days_five_ids')
    def _check_off_days_five_ids(self):
        for record in self:
            if len(record.off_days_five_ids) > 1:
                raise ValidationError("Off Days (5 Working Days per Week) can't add more than 1 lines")
    
    @api.constrains('break_off_six_ids')
    def _check_break_off_six_ids(self):
        for record in self:
            if len(record.break_off_six_ids) > 1:
                raise ValidationError("Off Days (6 Working Days per Week) can't add more than 1 lines")
    
    @api.constrains('off_days_public_ids')
    def _check_off_days_public_ids(self):
        for record in self:
            if len(record.off_days_public_ids) > 1:
                raise ValidationError("Public Holidays (Short Day) can't add more than 1 lines")

class Equip3OvertimeWorkdays(models.Model):
    _name = 'overtime.work.days.line'
    hour = fields.Float(string='Hours')
    values = fields.Float(string='Coefficient Hours')
    fix_amount = fields.Boolean()
    amount = fields.Float()
    overtime_id = fields.Many2one('overtime.rules')

    @api.onchange('fix_amount')
    def _onchange_fix_amount(self):
        for record in self:
            if record.fix_amount:
                record.values = 0
            if not record.fix_amount and record.amount > 0:
                record.amount=0

class OffDaysWorkingPerWeek(models.Model):
    _name = 'overtime.off.time.days'
    hour = fields.Float(string='Hours')
    values = fields.Float(string='Coefficient Hours')
    fix_amount = fields.Boolean()
    amount = fields.Float()
    overtime_id = fields.Many2one('overtime.rules')


    @api.onchange('fix_amount')
    def _onchange_fix_amount(self):
        for record in self:
            if record.fix_amount:
                record.values = 0
            if  not record.fix_amount  and record.amount > 0:
                record.amount = 0



class OffDaysWorkingDaysPerweek(models.Model):
    _name = 'overtime.off.time.days.week'
    hour = fields.Float(string='Hours')
    values = fields.Float(string='Coefficient Hours')
    fix_amount = fields.Boolean()
    amount = fields.Float()
    overtime_id = fields.Many2one('overtime.rules')



    @api.onchange('fix_amount')
    def _onchange_fix_amount(self):
        for record in self:
            if record.fix_amount:
                record.values = 0
            if not record.fix_amount and record.amount > 0:
                record.amount = 0



class PublicHolihay(models.Model):
    _name = 'overtime.off.public.holiday'
    hour = fields.Float(string='Hours')
    values = fields.Float(string='Coefficient Hours')
    fix_amount = fields.Boolean()
    amount = fields.Float()
    overtime_id = fields.Many2one('overtime.rules')


    @api.onchange('fix_amount')
    def _onchange_fix_amount(self):
        for record in self:
            if record.fix_amount:
                record.values = 0
            if  record.fix_amount == False and record.amount > 0:
                record.amount = 0

class MealAllowanceWorkDays(models.Model):
    _name = 'meal.allowance.work.days'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class MealAllowanceOfftimeFiveDays(models.Model):
    _name = 'meal.allowance.offtime.five.days'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class MealAllowanceOfftimeSixDays(models.Model):
    _name = 'meal.allowance.offtime.six.days'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class MealAllowanceOffPublicHoliday(models.Model):
    _name = 'meal.allowance.off.public.holiday'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class BreakTimeWorkDays(models.Model):
    _name = 'break.time.work.days'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class BreakTimeOfftimeFiveDays(models.Model):
    _name = 'break.time.offtime.five.days'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class BreakTimeOfftimeSixDays(models.Model):
    _name = 'break.time.offtime.six.days'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class BreakTimeOffPublicHoliday(models.Model):
    _name = 'break.time.off.public.holiday'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class OvertimeRounding(models.Model):
    _name = 'overtime.rounding'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minutes = fields.Integer(string='Minimum Minutes')
    rounding = fields.Integer(string='Rounding')

## Non Govenrment Rules ##
class OvertimeRulesLine(models.Model):
    _name = 'overtime.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    interval = fields.Float(string='Interval')
    amount = fields.Float(string='Amount')

class BreakOvertimeRulesLine(models.Model):
    _name = 'break.overtime.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class MealAllowanceOvertimeRulesLine(models.Model):
    _name = 'meal.allowance.overtime.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class OvertimeOffFiveRulesLine(models.Model):
    _name = 'overtime.off.five.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    interval = fields.Float(string='Interval')
    amount = fields.Float(string='Amount')

class BreakOffFiveRulesLine(models.Model):
    _name = 'break.off.five.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class MealAllowanceOffFiveRulesLine(models.Model):
    _name = 'meal.allowance.off.five.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class OvertimeOffSixRulesLine(models.Model):
    _name = 'overtime.off.six.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    interval = fields.Float(string='Interval')
    amount = fields.Float(string='Amount')

class BreakOffSixRulesLine(models.Model):
    _name = 'break.off.six.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class MealAllowanceOffSixRulesLine(models.Model):
    _name = 'meal.allowance.off.six.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')

class OvertimeOffPublicRulesLine(models.Model):
    _name = 'overtime.off.public.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    interval = fields.Float(string='Interval')
    amount = fields.Float(string='Amount')

class BreakOffPublicRulesLine(models.Model):
    _name = 'break.off.public.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    break_time = fields.Float(string='Break Time')

class MealAllowanceOffPublicRulesLine(models.Model):
    _name = 'meal.allowance.off.public.rules.line'

    overtime_rules_id = fields.Many2one('overtime.rules')
    minimum_hours = fields.Float(string='Minimum Hours')
    meal_allowance = fields.Float(string='Meal Allowance')