from odoo import models, fields, api, _
from odoo.tools.date_utils import start_of, end_of, add, subtract
from odoo.tools.misc import format_date
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_date_range(self):
        """ Return the date range for a production schedude depending the
        production period and the number of columns to display specify by the
        user. It returns a list of tuple that contains the timestamp for each
        column.
        """
        self.ensure_one()
        date_range = []
        period = self.manufacturing_period
        if period == 'month':
            first_day = start_of(fields.Date.today() + relativedelta(months=1), period)
        elif period == 'week':
            first_day = start_of(fields.Date.today() + relativedelta(weeks=1), period)
        else:
            first_day = start_of(fields.Date.today() + relativedelta(days=1), period)
        while first_day.weekday() in (5, 6):
            first_day += relativedelta(days=1)
        for columns in range(self.manufacturing_period_to_display):
            last_day = end_of(first_day, period)
            date_range.append((first_day, last_day))
            first_day = add(last_day, days=1)
            while first_day.weekday() in (5, 6):
                first_day += relativedelta(days=1)
        return date_range

    def date_range_to_str(self):
        date_range = self._get_date_range()
        dates_as_str = []
        lang = self.env.context.get('lang')
        for date_start, date_stop in date_range:
            if self.manufacturing_period == 'month':
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM yyyy'))
            elif self.manufacturing_period == 'week':
                dates_as_str.append(_('Week %s', format_date(self.env, date_start, date_format='w')))
            else:
                dates_as_str.append(format_date(self.env, date_start, date_format='MMM d'))
        return dates_as_str

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        for company in self:
            if company.id == self.env.company.id:
                mrp_mps_menu = self.env.ref('equip3_manuf_other_operations.mrp_mps_menu_planning')
                mrp_mps_menu.active = company.manufacturing_mps

        return res
