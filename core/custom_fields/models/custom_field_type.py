#coding: utf-8

from odoo import api, fields, models


class custom_field_type(models.AbstractModel):
    """
    The model to classify object by types

    During inheritance need to define _custom_field_model (e.g. custom.lead.field)
    """
    _name = "custom.field.type"
    _description = "Instance Type"
    _custom_field_model = []

    def _inverse_input_option(self):
        """
        Inverse method for name, active and input_option to re-generate xml view

        Methods:
         * _generate_xml of custom.field
        """
        for update_model in self._custom_field_model:
            self.env[update_model]._generate_xml()

    name = fields.Char(
        string="Name",
        required=True,
        inverse=_inverse_input_option,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        inverse=_inverse_input_option,
    )
    input_option = fields.Boolean(
        string="Input Option",
        default=True,
        inverse=_inverse_input_option,
    )
