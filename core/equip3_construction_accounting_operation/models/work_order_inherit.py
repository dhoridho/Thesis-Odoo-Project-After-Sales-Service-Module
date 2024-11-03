from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError


class ProjectTaskNewInherit(models.Model):
    _inherit = 'project.task'

    claim_id_so = fields.Many2one('progressive.claim', string="Claim Customer", ondelete='restrict', compute='_get_claim_so')
    claim_id_po = fields.Many2one('progressive.claim', string="Claim Subcon", ondelete='restrict', compute='_get_claim_po')
    labour_bill_count = fields.Integer(string='Labour Bill', compute='_compute_labour_bill_count')
    last_progress = fields.Float(string="Last Progress Claimed", digits=(2,2), compute="compute_last_progress")
    last_progress_subcon = fields.Float(string="Last Progress Subcon Claimed", digits=(2,2), compute="compute_last_progress_subcon")
    wo_prog_temp = fields.Float(string="Temporary (%)", compute="_compute_wo_prog_temp")
    claim_request = fields.Boolean(string="Claim Request", compute="compute_claim_request", store=True)
    is_greater_current_progress = fields.Boolean(string="Is Greater Current Progress", compute="compute_is_greater_current_progress")

    @api.depends('last_progress','progress_task')
    def _compute_wo_prog_temp(self):
        total = 0
        for res in self:
            total = res.progress_task - res.last_progress
            res.wo_prog_temp = total
        return total

    @api.depends('is_subcon')
    def compute_last_progress(self):
        for last in self:
            task_so = self.env['request.from.line'].search([('project_id', '=', last.project_id.id), ('progressive_bill', '=', False), ('contract_parent', '=', last.sale_order.id), ('work_order', '=', last.id)])
            total = 0
            if last.is_subcon == False:
                total = sum(task_so.mapped('wo_prog_temp'))
                last.last_progress = total
            else:
                last.last_progress = total
            return total
    
    @api.depends('is_subcon')
    def compute_last_progress_subcon(self):
        for last in self:
            # task_po = self.env['request.from.line'].search([('project_id', '=', last.project_id.id), ('progressive_bill', '=', True), ('contract_parent_po', '=', last.purchase_subcon.id), ('work_order_sub', '=', last.id)])
            task_po = self.env['request.from.line'].search([('project_id', '=', last.project_id.id), ('progressive_bill', '=', True), ('task_contract_po', '=', last.purchase_subcon.id), ('work_order_sub', '=', last.id)])
            total = 0
            if last.is_subcon == True:
                total = sum(task_po.mapped('wo_prog_temp'))
                last.last_progress_subcon = total
            else:
                last.last_progress_subcon = total
            return total

    @api.depends('progress_task','last_progress')
    def compute_claim_request(self):
        for res in self:
            if res.progress_task > res.last_progress:
                res.claim_request = True
            elif res.progress_task == res.last_progress:
                res.claim_request = False
            else:
                res.claim_request = False
    
    @api.depends('last_progress', 'progress_task')
    def compute_is_greater_current_progress(self):
        for rec in self:
            if not rec.is_subcon:
                if rec.progress_task > rec.last_progress:
                    rec.is_greater_current_progress = True
                else:
                    rec.is_greater_current_progress = False
            else:
                if rec.progress_task > rec.last_progress_subcon:
                    rec.is_greater_current_progress = True
                else:
                    rec.is_greater_current_progress = False

    def _get_claim_so(self):
        claim_id = False
        claim_id = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent', '=', self.sale_order.id), ('progressive_bill', '=', False), ('state', 'in', ('in_progress','done'))], limit=1)
        self.claim_id_so = claim_id

    def _compute_labour_bill_count(self):
        for rec in self:
            if rec.is_subtask:
                project_task = rec._get_subtask_parents()
            else:
                project_task = rec
            rec.env.cr.execute(
                "SELECT count(*) FROM account_move WHERE project_task_id = %s",
                (project_task.id,))
            labour_bill_count = rec.env.cr.fetchone()[0]
            rec.labour_bill_count = labour_bill_count

    def action_claim_so_cons(self):
        action = self.claim_id_so.get_formview_action()
        action['domain'] = [('id', '=', self.claim_id_so.id)]
        return action
    
    def _get_claim_po(self):
        claim_id = False
        claim_id = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent_po', '=', self.purchase_subcon.id), ('progressive_bill', '=', True), ('state', 'in', ('in_progress','done'))], limit=1)
        self.claim_id_po = claim_id

    def action_claim_po_cons(self):
        action = self.claim_id_po.get_formview_action()
        action['domain'] = [('id', '=', self.claim_id_po.id)]
        return action

    def action_view_labour_bills(self):
        if self.is_subtask:
            project_task = self._get_subtask_parents()
        else:
            project_task = self
        return {
            'name': ("Labour Bills"),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_task_id', '=', project_task.id)],
        }