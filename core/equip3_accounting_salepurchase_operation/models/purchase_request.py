# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
    
    def action_confirm_purchase_request_wizard(self):
        for req in self:
            for line in req.line_ids:
                if line.price_total > line.remaining_amount_budget:
                    raise UserError(_("Unable to process your request due to over budget"))
    
    def button_to_approve(self):
        exceeding_lines = []
        for req in self:
            for line in req.line_ids:
                if line.purchase_req_budget_2 != 0:
                # if line.price_total > line.remaining_amount_budget:
                    if line.price_total > line.avail_amount_budget:
                        exceeding_lines.append((0,0,{'product_id':line.product_id.id, 
                                                     'purchase_req_budget':round(line.purchase_req_budget_2,2), 
                                                     'available_budget':round(line.avail_amount_budget,2),
                                                     'reserved_budget':round(line.reserve_amount_budget,2),
                                                     'realized_amount':round(line.price_total,2)}))
        if exceeding_lines:
            return {
                'name': _('Warning'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.request.warning',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {'default_name': 'Warning', 'default_warning_line_ids': exceeding_lines}
            }
        else :
            res = super(PurchaseRequest, self).button_to_approve()
            return res
        

    # def button_approved(self):
    #     exceeding_lines = []
    #     for req in self:
    #         for line in req.line_ids:
    #             if line.price_total > line.avail_amount_budget:
    #                 exceeding_lines.append((0,0,{'product_id':line.product_id.id, 
    #                                              'purchase_req_budget':round(line.purchase_req_budget_2,2), 
    #                                              'available_budget':round(line.avail_amount_budget,2),
    #                                              'reserved_budget':round(line.reserve_amount_budget,2),
    #                                              'realized_amount':round(line.price_total,2)}))
    #     if exceeding_lines:
    #         raise UserError(_("You can't approve this Purchase Request because reserve amount is not available "
    #                           "Reject this Purchase Request or ask for Purchase Budget Change Request"))
    #     else :
    #         res = super(PurchaseRequest, self).button_approved()
    #         return res
        
    

    def action_confirm_purchase_request(self):
        # for req in self:
        #     req.action_confirm_purchase_request_wizard()

        res = super(PurchaseRequest, self).action_confirm_purchase_request()
        for req in self:
            for line in req.line_ids:
                line.write({
                    'confirm_purchase_req_budget' : line.purchase_req_budget_2,
                    'confirm_realized_amount' : line.realized_amount, 
                    'confirm_remaining_amount' : line.remaining_amount_budget, 
                    'confirm_avail_amount' : line.avail_amount_budget, 
                    'confirm_reserve_amount' : line.reserve_amount_budget, 
                    'confirm_budget_data' : True
                })
        return res

class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"
    
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
    purchase_req_budget_2 = fields.Monetary("Purchase Budget", compute='_get_purchase_req_budget', readonly=True)
    # purchase_req_budget_2 = fields.Float("Purchase Budget", readonly=True)
    realized_amount = fields.Float("Realized Budget")
    confirm_purchase_req_budget = fields.Float("Confirmed Purchase Request Budget")
    confirm_realized_amount = fields.Float("Confirmed Realized Budget")
    confirm_remaining_amount = fields.Float("Confirmed Remaining Budget")
    confirm_avail_amount = fields.Float("Confirmed Avail Budget")
    confirm_reserve_amount = fields.Float("Confirmed Reserve Budget")
    confirm_budget_data = fields.Boolean(default=False)
    remaining_amount_budget = fields.Monetary("Remaining Budget", compute='_get_purchase_req_budget', readonly=True)
    avail_amount_budget = fields.Monetary('Available to Reserve', compute='_get_purchase_req_budget', readonly=True)
    reserve_amount_budget = fields.Monetary('Reserved Budget', compute='_get_purchase_req_budget', readonly=True)


    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     for rec in self:
    #         purchase_req_budget = 0
    #         realized_amount = 0
    #         remaining_amount = 0
    #         gop = rec.product_id.product_tmpl_id.group_product
    #         budget_purchase_line_filter = [('date_from','<=',fields.Date.today()),('date_to','>=',fields.Date.today()),('group_product_id','=',gop.id)]
    #         budget_purchase_lines = self.env['budget.purchase.lines'].search(budget_purchase_line_filter)
    #         purchase_req_budget = budget_purchase_lines and sum([x.planned_amount for x in budget_purchase_lines if x.purchase_budget_state in ('done','validate')]) or 0
    #         realized_amount = budget_purchase_lines and sum([x.practical_amount for x in budget_purchase_lines if x.purchase_budget_id.state in ('done','validate')]) or 0
    #         remaining_amount = budget_purchase_lines and sum([x.remaining_amount for x in budget_purchase_lines if x.purchase_budget_state in ('done','validate')]) or 0
    #         rec.purchase_req_budget_2 = purchase_req_budget
    #         rec.realized_amount = realized_amount
    #         rec.remaining_amount_budget = remaining_amount
            

    
    @api.depends('product_id','analytic_account_group_ids','request_id.request_date','currency_id')
    def _get_purchase_req_budget(self):
        today = fields.Date.today()
        request_date = self.request_id.request_date
        for rec in self:
            purchase_req_budget = 0
            realized_amount = 0
            remaining_amount = 0
            avail_amount = 0
            reserve_amount = 0


            if rec.confirm_budget_data:
                purchase_req_budget = rec.confirm_purchase_req_budget
                realized_amount = rec.confirm_realized_amount
                remaining_amount = rec.confirm_remaining_amount
                avail_amount = rec.confirm_avail_amount
                reserve_amount = rec.confirm_reserve_amount

            elif rec.product_id:
                domain = [
                    # '&', ('date_from', '<', request_date), ('date_to', '>', request_date),  # Overlapping condition
                    # '|',('date_from', '>', request_date), ('date_to', '<', request_date),  # Starting condition
                    ('account_tag_ids', 'in', rec.analytic_account_group_ids.ids),
                    ('product_budget', '!=', False),
                    ('date_from', '<=', request_date), ('date_to', '>=', request_date),
                    ('product_id', '=', rec.product_id.id), ('purchase_budget_state', 'in', ('confirm','validate')),
                    ('purchase_budget_id.is_parent_budget','=',False),
                ]
                product_budget_lines = self.env['budget.purchase.lines'].search(domain)
                gop = rec.product_id.product_tmpl_id.group_product
                # budget_purchase_line_filter = [('product_id','=',rec.product_id.id),('date_from','<=',today),('date_to','>=',today),('account_tag_ids','in',rec.analytic_account_group_ids.ids)]
                # budget_purchase_lines = self.env['budget.purchase.lines'].search(budget_purchase_line_filter)
                # budget_purchase_line_filter = [('date_from','<=',request_date),('date_to','>=',request_date),('group_product_id','=',gop.id)]
                # budget_purchase_lines = self.env['budget.purchase.lines'].search(budget_purchase_line_filter)

                if product_budget_lines:
                    for result in product_budget_lines:
                        result._compute_fields_practical()
                        avail_amount = result.currency_id._convert(result.avail_amount, rec.currency_id, rec.company_id, request_date) or 0
                        purchase_req_budget = result.currency_id._convert(result.planned_amount, rec.currency_id, rec.company_id, request_date) or 0
                        realized_amount = result.currency_id._convert(result.practical_amount, rec.currency_id, rec.company_id, request_date) or 0
                        remaining_amount = result.currency_id._convert(result.remaining_amount, rec.currency_id, rec.company_id, request_date) or 0
                        reserve_amount = result.currency_id._convert(result.reserve_amount, rec.currency_id, rec.company_id, request_date) or 0
                elif gop.id:
                    domain = [
                        ('account_tag_ids', 'in', rec.analytic_account_group_ids.ids), 
                        ('monthly_purchase_budget_id.date_from', '<=', request_date), ('monthly_purchase_budget_id.date_to', '>=', request_date), 
                        ('group_product_id', '=', gop.id), ('monthly_purchase_budget_id.state', '=', 'validate'),
                    ]
                    results = self.env['monthly.purchase.budget.line'].search(domain)

                    for result in results:
                        avail_amount = result.currency_id._convert(result.avail_amount, rec.currency_id, rec.company_id, request_date) or 0
                        purchase_req_budget = result.currency_id._convert(result.planned_amount, rec.currency_id, rec.company_id, request_date) or 0
                        realized_amount = result.currency_id._convert(result.practical_amount, rec.currency_id, rec.company_id, request_date) or 0
                        remaining_amount = result.currency_id._convert(result.remaining_amount, rec.currency_id, rec.company_id, request_date) or 0
                        reserve_amount = result.currency_id._convert(result.reserve_amount, rec.currency_id, rec.company_id, request_date) or 0

                    if not results:
                        domain = [
                            # '|',
                            # '&', ('date_from', '<', request_date), ('date_to', '>', request_date),  # Overlapping condition
                            # '|',('date_from', '>', request_date), ('date_to', '<', request_date),  # Starting condition
                            ('account_tag_ids', 'in', rec.analytic_account_group_ids.ids), 
                            ('date_from', '<=', request_date), ('date_to', '>=', request_date), 
                            ('group_product_id', '=', gop.id), ('purchase_budget_state', 'in', ('confirm','validate')),
                            ('purchase_budget_id.is_parent_budget','=',False),
                        ]
                        results = self.env['budget.purchase.lines'].search(domain)

                        for result in results:
                            result._compute_fields_practical()
                            avail_amount = result.currency_id._convert(result.avail_amount, rec.currency_id, rec.company_id, request_date) or 0
                            purchase_req_budget = result.currency_id._convert(result.planned_amount, rec.currency_id, rec.company_id, request_date) or 0
                            realized_amount = result.currency_id._convert(result.practical_amount, rec.currency_id, rec.company_id, request_date) or 0
                            remaining_amount = result.currency_id._convert(result.remaining_amount, rec.currency_id, rec.company_id, request_date) or 0
                            reserve_amount = result.currency_id._convert(result.reserve_amount, rec.currency_id, rec.company_id, request_date) or 0
                    # purchase_req_budget = sum([x.planned_amount for x in results if x.purchase_budget_state in ('done','validate')]) or 0
                    # realized_amount = sum([x.practical_amount for x in results if x.purchase_budget_id.state in ('done','validate')]) or 0
                    # remaining_amount = sum([x.remaining_amount for x in results if x.purchase_budget_state in ('done','validate')]) or 0
                else:
                    # Handle the case where 'gop' does not have a valid ID (e.g., it's a new record not yet saved)
                    # This might involve skipping the search or taking some other action
                    domain = [
                        ('account_tag_ids', 'in', rec.analytic_account_group_ids.ids), 
                        ('monthly_purchase_budget_id.date_from', '<=', request_date), ('monthly_purchase_budget_id.date_to', '>=', request_date), 
                        ('product_id', '=', rec.product_id.id), ('monthly_purchase_budget_id.state', '=', 'validate'),
                    ]
                    results = self.env['monthly.purchase.budget.line'].search(domain)

                    for result in results:
                        avail_amount = result.currency_id._convert(result.avail_amount, rec.currency_id, rec.company_id, request_date) or 0
                        purchase_req_budget = result.currency_id._convert(result.planned_amount, rec.currency_id, rec.company_id, request_date) or 0
                        realized_amount = result.currency_id._convert(result.practical_amount, rec.currency_id, rec.company_id, request_date) or 0
                        remaining_amount = result.currency_id._convert(result.remaining_amount, rec.currency_id, rec.company_id, request_date) or 0
                        reserve_amount = result.currency_id._convert(result.reserve_amount, rec.currency_id, rec.company_id, request_date) or 0

                    if not results:
                        domain = [
                            # '&', ('date_from', '<', request_date), ('date_to', '>', request_date),  # Overlapping condition
                            # '|',('date_from', '>', request_date), ('date_to', '<', request_date),  # Starting condition
                            ('account_tag_ids', 'in', rec.analytic_account_group_ids.ids), 
                            ('date_from', '<=', request_date), ('date_to', '>=', request_date), 
                            ('product_id', '=', rec.product_id.id), ('purchase_budget_state', 'in', ('confirm','validate')),
                            ('purchase_budget_id.is_parent_budget','=',False),
                        ]
                        results = self.env['budget.purchase.lines'].search(domain)

                        for result in results:
                            result._compute_fields_practical()
                            avail_amount = result.currency_id._convert(result.avail_amount, rec.currency_id, rec.company_id, request_date) or 0
                            purchase_req_budget = result.currency_id._convert(result.planned_amount, rec.currency_id, rec.company_id, request_date) or 0
                            realized_amount = result.currency_id._convert(result.practical_amount, rec.currency_id, rec.company_id, request_date) or 0
                            remaining_amount = result.currency_id._convert(result.remaining_amount, rec.currency_id, rec.company_id, request_date) or 0
                            reserve_amount = result.currency_id._convert(result.reserve_amount, rec.currency_id, rec.company_id, request_date) or 0

            rec.purchase_req_budget_2 = purchase_req_budget
            rec.realized_amount = realized_amount
            rec.remaining_amount_budget = remaining_amount
            rec.avail_amount_budget = avail_amount
            rec.reserve_amount_budget = reserve_amount