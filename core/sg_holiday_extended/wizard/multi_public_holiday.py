from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class MultiPublicHoliday(models.TransientModel):
    _name = 'multi.public.holiday'
    _description = "Multi Public Holiday"

    name = fields.Char('Holiday Name', required=True)
    start_date = fields.Date('From Date', help='Holiday Start date',
                             required=True)
    end_date = fields.Date('To Date', help='Holiday End date',
                           required=True)

    @api.constrains('start_date', 'end_date')
    def _check_public_date(self):
        if self.start_date > self.end_date:
            raise ValidationError(_(
                'The start date must be anterior to the end date.'))
        return True

    def cerate_public_holiday(self):
        context = self.env.context
        holiday_line_obj = self.env['hr.holiday.lines']
        pub_holiday_obj = self.env['hr.holiday.public']
        res_day = ''
        daylist = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                   'Saturday', 'Sunday']
        if context and context.get('active_ids'):
            pub_hol_ids = pub_holiday_obj.browse(context.get('active_ids'))
            if len(pub_hol_ids) > 1:
                state_lst = [pub_hol_id.id for pub_hol_id in pub_hol_ids if pub_hol_id.state not in ['validated', 'confirmed']]
                if len(state_lst) > 0:
                    for pub_hol_id in pub_hol_ids:
                        if pub_hol_id.state not in ['validated', 'confirmed']:
                            starting_date = self.start_date
                            if starting_date and self.end_date:
                                end_date = datetime.strftime(self.end_date,
                                                             DSDF)
                                while datetime.strftime(starting_date, DSDF) \
                                        <= end_date:
                                    s_date = starting_date + relativedelta(
                                        days=1)
                                    res = datetime.strftime(s_date, DSDF)
                                    start_year = starting_date.year
                                    if pub_hol_id.name == str(start_year):
                                        if starting_date:
                                            day = starting_date.weekday()
                                            res_day = daylist[day]
                                        line_ids = holiday_line_obj.search([
                                            ('holiday_id', '=', pub_hol_id.id),
                                            ('holiday_date', '=',
                                             datetime.strftime(starting_date,
                                                               DSDF))])
                                        if not line_ids:
                                            result = {
                                                'holiday_date': starting_date,
                                                'name': self.name or '',
                                                'holiday_id': pub_hol_id.id,
                                                'day': res_day or '',
                                            }
                                            holiday_line_obj.create(result)
                                    starting_date = datetime.strptime(res, DSDF)
                else:
                    raise ValidationError(_("Sorry !\n You can't update"
                                          "confirmed public holiday."))
            else:
                if len(pub_hol_ids) == 1:
                    if pub_hol_ids.state not in ['validated', 'confirmed']:
                        starting_date = self.start_date
                        if ((starting_date and self.end_date) and
                            (str(starting_date.year) == pub_hol_ids.name or
                             str(self.end_date.year) == pub_hol_ids.name)):
                            end_date = datetime.strftime(self.end_date, DSDF)
                            while datetime.strftime(starting_date, DSDF) <=\
                                    end_date:
                                s_date = starting_date + relativedelta(days=1)
                                res = datetime.strftime(s_date, DSDF)
                                start_year = starting_date.year
                                if pub_hol_ids.name == str(start_year):
                                    if starting_date:
                                        day = starting_date.weekday()
                                        res_day = daylist[day]
                                    line_ids = holiday_line_obj.search([
                                        ('holiday_id', '=', pub_hol_ids.id),
                                        ('holiday_date', '=',
                                         datetime.strftime(starting_date,
                                                           DSDF))])
                                    if not line_ids:
                                        result = {
                                            'holiday_date': starting_date,
                                            'name': self.name or '',
                                            'holiday_id': pub_hol_ids.id,
                                            'day': res_day or '',
                                        }
                                        holiday_line_obj.create(result)
                                starting_date = datetime.strptime(res, DSDF)
                        else:
                            raise ValidationError(_(
                                "Sorry !\n You can't generate "
                                "public holiday for different year"))
                    else:
                        raise ValidationError(_("Sorry !\n You can't update "
                                              "confirmed public holiday."))
        return True
