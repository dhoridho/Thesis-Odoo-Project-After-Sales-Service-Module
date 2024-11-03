from odoo import _, api, fields, models
from datetime import date, datetime


class ClassRoom(models.Model):
    _name = "class.room"
    _inherit = ["class.room", "mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(track_visibility='onchange')
    capacity = fields.Integer(string="Capacity", track_visibility='onchange')
    equipment_ids = fields.Many2many('school.equipment', string="Equipment", domain="[('active','=',True)]")
    class_ids = fields.One2many('school.standard','class_room_id', string='Intake')
    classes_ids = fields.One2many('ems.classes','classroom_id')
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
    active = fields.Boolean(default=True, help="Activate/Deactivate Class Room")

    def write(self, vals):
        if 'equipment_ids' in vals:
            initial_equipment = set(self.equipment_ids.ids)
            current_equipment = set(vals['equipment_ids'][0][2])
            deleted_ids = initial_equipment - current_equipment
            
            if deleted_ids:
                for deleted_id in deleted_ids:
                    deleted = self.env['school.equipment'].browse(deleted_id)
                    message_body = 'Equipment (%s) is Removed' % (deleted.name)
                    self.message_post(body=message_body)

        return super(ClassRoom, self).write(vals)

class EMSPublicHoliday(models.Model):
    _name = 'ems.public.holiday'
    _description = 'Public Holiday'

    name = fields.Char(string='Name of Holiday', required=True)
    date = fields.Date(string='Date', required=True)

class Equip3School(models.Model):
    _inherit = 'school.school'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        ondelete="cascade",
        required=True,
        delegate=False,
        help='Company_id of the school'
    )
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        string="Fed. State",
        domain="[('country_id', '=?', country_id)]"
    )
    country_id = fields.Many2one(comodel_name='res.country', string="Country")
    active = fields.Boolean(
        default=True, help="Activate/Deactivate School"
    )

    @api.model
    def create(self, vals):
        main_company = self.env.ref('base.main_company')
        self.company_id.parent_id = main_company.id
        res = super(Equip3School, self).create(vals)

        return res


class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Company"
    )


class ResBranchInherit(models.Model):
    _inherit = "res.branch"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Company"
    )


class GradeMasterInherit(models.Model):
    _inherit = "grade.master"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Grade"
    )


class MotherTongueInherit(models.Model):
    _inherit = "mother.toungue"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Mother Tongue"
    )

class StudentCastInherit(models.Model):
    _inherit = "student.cast"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Religion"
    )


class StudentNewsINherit(models.Model):
    _inherit = "student.news"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Noticeboard"
    )


class EmsPublicHolidayInherit(models.Model):
    _inherit = "ems.public.holiday"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Public Holiday"
    )
