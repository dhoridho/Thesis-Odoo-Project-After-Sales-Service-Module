# Part of Softhealer Technologies.
from odoo import models, fields


class Annoucement(models.Model):
    _name = 'sh.annoucement'
    _description = 'Announcement'
    _order = "sequence,id"

    sequence = fields.Integer(default=10,
                              help="Gives the sequence of annoucmeent")
    name = fields.Text("Annoucement", required="1")
    date = fields.Date("Date", required="1")
    active = fields.Boolean(default=True)
