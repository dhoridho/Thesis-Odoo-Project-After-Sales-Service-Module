from odoo import api, fields, models, _


class Equip3MaintenanceEquipment(models.Model):
    _name = "aftersale.maintenance.team"
    _description = "Aftersale Maintenance Team"

    name = fields.Char(_("Name"))
    leader_id = fields.Many2one("res.users", _("Leader"))
    company_id = fields.Many2one(
        "res.company", _("Company"), default=lambda self: self.env.user.company_id
    )
    description = fields.Text(_("Description"))


class Equip3FacilityArea(models.Model):
    _name = "aftersale.facility.area"
    _description = "Aftersale Facility Area"

    name = fields.Char(_("Name"))
    parent_id = fields.Many2one("aftersale.facility.area", _("Parent Area"))
    note = fields.Char(_("Internal Note"))
    company_id = fields.Many2one(
        "res.company", _("Company"), default=lambda self: self.env.user.company_id
    )
    branch_id = fields.Many2one("res.branch", _("Branch"))
    location_id = fields.Many2one("stock.location", string=_("Location"))
