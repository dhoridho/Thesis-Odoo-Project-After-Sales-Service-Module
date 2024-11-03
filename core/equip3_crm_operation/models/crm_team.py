from odoo import fields,api, models, _
from odoo.exceptions import ValidationError
from operator import itemgetter

class CrmTeam(models.Model):
    _inherit = "crm.team"

    parent_team_id = fields.Many2one('crm.team', string="Parent Team")
    additional_leader_ids = fields.Many2many('res.users', string="Additional Leader")
    child_team_ids = fields.One2many('crm.team','parent_team_id', string="Child Team")
    res_name = fields.Char("Name", compute='_compute_res_name', store=False)
    list_parent_team_ids = fields.Many2many('crm.team','child_parent_team_id_rel', 'child_id', 'parent_id',  string='List Parent Team', compute='_compute_list_parent_team_ids', store=True)
    list_child_team_ids = fields.Many2many('crm.team','parent_child_team_id_rel', 'parent_id', 'child_id',  string='List Child Team')
    list_crm_target_ids = fields.One2many('crm.target','sale_team_id', string="Salesperson Target")

    def _set_child_team_ids(self,parent_team_id,new_parent_team_id):
        for rec in self:
            # mendata list child dari team
            if parent_team_id and self.env.context.get('from_create'):
                parent_team_id.list_child_team_ids = [(4, rec.id)]
                if parent_team_id.list_parent_team_ids:
                    for parent in parent_team_id.list_parent_team_ids:
                        parent.list_child_team_ids = [(4, rec.id)]
            if self.env.context.get('from_write'):
                if parent_team_id:
                    parent_team_id.list_child_team_ids = [(3, rec.id)]
                    if parent_team_id.list_parent_team_ids:
                        for parent in parent_team_id.list_parent_team_ids:
                            parent.list_child_team_ids = [(3, rec.id)]
                new_parent_team_id = self.env['crm.team'].browse(new_parent_team_id)
                new_parent_team_id.list_child_team_ids = [(4, rec.id)]
                if new_parent_team_id.list_parent_team_ids:
                    for parent in new_parent_team_id.list_parent_team_ids:
                        parent.list_child_team_ids = [(4, rec.id)]

    @api.depends('parent_team_id')
    def _compute_list_parent_team_ids(self):
        # funct untuk mendapatkan list parent dari team
        for rec in self:
            list_parent_team_ids = []
            if rec.parent_team_id:
                if self.parent_team_id.list_parent_team_ids:
                    list_parent_team_ids.extend(self.parent_team_id.list_parent_team_ids.ids)
                list_parent_team_ids.append(self.parent_team_id.id)
            rec.list_parent_team_ids = [(6,0,list_parent_team_ids)]

    @api.depends('list_parent_team_ids','parent_team_id')
    def _compute_res_name(self):
        for rec in self:
            res_name = ''
            if rec.list_parent_team_ids:
                res_name = ' / '.join(rec.list_parent_team_ids.mapped('name')) + ' / ' + rec.name
            else:
                res_name += rec.name
            rec.res_name = res_name

    def set_list_user_id_for_additional_leader(self, additional_leader_ids):
        # funct untuk mendapatkan list member bagi additional leader
        for additional_leader in additional_leader_ids:
            team_ids = self.env['crm.team'].search(['|',('user_id','=', additional_leader.id),('additional_leader_ids','in',additional_leader.id)])
            if team_ids:
                list_user_id = additional_leader.list_user_id
                list_member_ids = []
                if not list_user_id:
                    list_user_id = self.env['list.user'].create({})
                for my_team in team_ids:
                    list_member_ids.extend(my_team.member_ids.ids)
                    for child_team in my_team.list_child_team_ids:
                        list_member_ids.extend(child_team.member_ids.ids)
                list_user_id.user_ids = [(6, 0, list_member_ids)]
                additional_leader.list_user_id = list_user_id
            else:
                additional_leader.list_user_id = False

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.list_parent_team_ids:
            res.with_context(from_create=True)._set_child_team_ids(res.parent_team_id,False)
        if res.additional_leader_ids:
            res.set_list_user_id_for_additional_leader(res.additional_leader_ids)
        return res

    def write(self, vals):
        if 'parent_team_id' in vals:
            self.with_context(from_write=True)._set_child_team_ids(self.parent_team_id, vals['parent_team_id'])
        additional_leader_ids = self.additional_leader_ids
        res = super().write(vals)
        if self.additional_leader_ids != additional_leader_ids:
            # mengatur list member untuk additional leader apabila terjadi perubahan, baik penambahan ataupun pengurangan additional leader
            all_additional_leader_ids = list(set(self.additional_leader_ids) | set(additional_leader_ids))
            self.set_list_user_id_for_additional_leader(all_additional_leader_ids)
        if 'member_ids' in vals:
            # mengatur list member untuk additional leader apabila terjadi perubahan, baik penambahan ataupun pengurangan member
            all_leader_ids = []
            all_leader_ids.extend(self.additional_leader_ids)
            all_leader_ids.extend(self.list_parent_team_ids.mapped('additional_leader_ids'))
            self.set_list_user_id_for_additional_leader(list(set(all_leader_ids)))
        return res