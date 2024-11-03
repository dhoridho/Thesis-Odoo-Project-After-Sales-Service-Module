from odoo import models, fields, api, _


class MiningTimesheetActivity(models.Model):
    _name = 'mining.timesheet.activity'
    _description = 'Mining Timesheet Activity'

    name = fields.Char(string="Activity Name", required=True)
    activity_type = fields.Selection(
        selection=[
            ('operative', 'Operative'),
            ('idle', 'Idle'),
            ('breakdown', 'Breakdown')
        ],
        string='Activity Type',
        default='operative',
        required=True
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True,
        required=True)

    branch_id = fields.Many2one(
        comodel_name='res.branch',
        string='Branch', required=True)

    create_uid = fields.Many2one(
        comodel_name='res.users',
        string='Created By',
        default=lambda self: self.env.user,
        tracking=True)
