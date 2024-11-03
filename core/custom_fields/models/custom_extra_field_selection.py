# -*- coding: utf-8 -*-

from odoo import api, fields, models


class custom_extra_field_selection_option(models.Model):
    """
    The model to keep options of selection fields
    """
    _name = 'custom.extra.field.selection'
    _description = 'Selection Option'

    @api.model
    def _default_sequence(self):
        """
        Default method for sequence as previous one plus 1
        """
        last_option = self.search([], limit=1, order='sequence desc')
        return bool(last_option) and last_option.sequence + 1 or 1

    @api.depends("value")
    def _compute_name(self):
        """
        Compute method for name
        """
        for option in self:
            option.name = option.value

    sequence = fields.Integer(
        string='Sequence',
        default=_default_sequence,
    )
    field_id = fields.Integer(string="Related Document ID")
    key = fields.Char(
        'Key',
        required=False,
    )
    value = fields.Char('Value', required=True)
    name = fields.Char(
        compute="_compute_name",
        compute_sudo=True,
        string='Name'
    )
    model = fields.Char(string="Related document model")

    _order = 'sequence, id'

    @api.model
    def create(self, values):
        """
        Overwriting to assign a key as "x_option" + "id"
        """
        option_id = super(custom_extra_field_selection_option, self).create(values)
        option_id.key = "x_option_{}".format(option_id.id)
        return option_id
