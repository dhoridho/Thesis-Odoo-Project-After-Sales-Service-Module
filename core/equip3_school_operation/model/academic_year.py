from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class AcademicMonth(models.Model):
    _inherit = "academic.month"
    _order = "create_date desc"

    billing_date = fields.Date(string="Billing Date")

    @api.constrains('year_id', 'date_start', 'date_stop')
    def _check_year_limit(self):
        '''Method to check year limit'''
        for record in self:
            if record.year_id and record.date_start and record.date_stop:
                if (record.year_id.date_stop < record.date_stop or
                        record.year_id.date_stop < record.date_start or
                        record.year_id.date_start > record.date_start or
                        record.year_id.date_start > record.date_stop):
                    raise ValidationError(_("Start of Period and End of Period Out of Start Date and End Date. Please check again!"))

    @api.constrains('billing_date', 'date_stop')
    def _check_billing_date(self):
        for record in self:
            if record.billing_date > record.date_stop:
                raise ValidationError(_("Billing date should be not greater then End of Period"))

    # @api.constrains('enrollment_date_start', 'enrollment_date_stop')
    # def _check_enrollment_date(self):
    #     enrollment_date = self.search([('id', 'not in', self.ids)])
    #     for old_month in enrollment_date:
    #         if old_month.enrollment_date_start <= \
    #                 old_month.enrollment_date_start <= old_month.enrollment_date_stop \
    #                 or old_month.enrollment_date_start <= \
    #                 old_month.enrollment_date_stop <= old_month.enrollment_date_stop:
    #             raise ValidationError(_("Enrollment Date is Overlapping"))
