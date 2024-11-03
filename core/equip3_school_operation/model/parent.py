from odoo import api, fields, models, _, tools

class SchoolParent(models.Model):
    _name = 'school.parent'
    _inherit = ["school.parent", "mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    message_ids = fields.One2many(
        "mail.message",
        "res_id",
        "Messages",
        domain=lambda self: [("model", "=", self._name)],
        auto_join=True,
        help="Messages can entered",
    )
    message_follower_ids = fields.One2many(
        "mail.followers",
        "res_id",
        "Followers",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Select message followers",
    )
    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user", )

    @api.model
    def create(self, values):
        res = super(SchoolParent, self).create(values)
        res.partner_id.user_ids.write({'groups_id': [(4, self.env.ref('school.group_school_parent').id)]})
        return res 