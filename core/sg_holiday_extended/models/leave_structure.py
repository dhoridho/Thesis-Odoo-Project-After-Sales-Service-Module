from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SgLeaveContract(models.Model):
    _name = 'holiday.group.config'
    _description = "Holiday Group Config"

    name = fields.Char("Name")
    holiday_group_config_line_ids = fields.One2many(
        'holiday.group.config.line',
        'holiday_group_config_id',
        'Config Line')


class HolidayGroupConfigLine(models.Model):
    _name = 'holiday.group.config.line'
    _description = "Holiday Group Config Line"
    _rec_name='leave_type_id'

    holiday_group_config_id = fields.Many2one('holiday.group.config',
                                              'Leave Types')
    leave_type_id = fields.Many2one('hr.leave.type')
    default_leave_allocation = fields.Float('Default Annual Leave')
    incr_leave_per_year = fields.Float('Increment Leaves Per Year')
    max_leave_kept = fields.Float('Maximum Leave')
    carryover = fields.Selection([('none', 'None'),
                                  ('up_to', '50% of Entitlement'),
                                  ('no_of_days', 'Number of Days'),
                                  ('unlimited', 'Unlimited')],
                                 default="unlimited", string="Carryover")
    carry_no_of_days = fields.Float("Number of Days")

    @api.constrains('leave_type_id')
    def _check_multiple_leaves_configured(self):
        """Check multiple leave configuration.

        This constrain method is used to restrict the system
        that do not configure same leave for multiple time.
        """
        for holiday in self:
            if holiday.holiday_group_config_id and\
                    holiday.holiday_group_config_id.id:
                domain = [('leave_type_id', '=', holiday.leave_type_id.id),
                          ('holiday_group_config_id', '=',
                           holiday.holiday_group_config_id.id),
                          ('id', '!=', holiday.id)]
                nholidays = self.search(domain, limit=1)
                if nholidays:
                    raise ValidationError(_(
                        "You can not add multiple configurations for leave"
                        " type '%s'." % (holiday.leave_type_id.name2)))
