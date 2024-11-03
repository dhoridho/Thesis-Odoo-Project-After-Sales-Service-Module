from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TermCondition(models.Model):
    _name = 'term.condition'
    _description = 'Term Condition'

    name = fields.Char("Name")
    description = fields.Char("Description")
    term_condition = fields.Html("Terms & Conditions")