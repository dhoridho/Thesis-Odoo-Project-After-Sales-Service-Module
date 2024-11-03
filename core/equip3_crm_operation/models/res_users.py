# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    list_user_id = fields.Many2one('list.user', compute='_compute_list_user_id', string='List User', store=True)
    my_team_ids = fields.One2many('crm.team','user_id', string="My Team")

    @api.depends('my_team_ids','my_team_ids.list_child_team_ids','my_team_ids.member_ids')
    def _compute_list_user_id(self):
        # funct untuk mendapatkan list member bagi leader dari team dan childnya
        for rec in self:
            if rec.my_team_ids:
                list_user_id = rec.list_user_id
                list_member_ids = []
                if not list_user_id:
                    list_user_id = self.env['list.user'].create({})
                for my_team in rec.my_team_ids:
                    list_member_ids.extend(my_team.member_ids.ids)
                    for child_team in my_team.list_child_team_ids:
                        list_member_ids.extend(child_team.member_ids.ids)
                list_user_id.user_ids = [(6, 0, list_member_ids)]
            else:
                list_user_id = False
            rec.list_user_id = list_user_id


class ListUser(models.Model):
    _name = "list.user"
    _description = "List User"

    user_ids = fields.Many2many('res.users', string='User')