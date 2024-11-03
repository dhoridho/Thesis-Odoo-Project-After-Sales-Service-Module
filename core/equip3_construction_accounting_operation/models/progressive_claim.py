from operator import truediv
import time
from urllib import request
from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
from calendar import Calendar
from dateutil.relativedelta import relativedelta


class ProgressiveClaim(models.Model):
    _name = 'progressive.claim'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True
    _description = "Progressive Claim"

    # Remove submenu report button
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu
        )
        if res.get('toolbar', False) and res.get('toolbar').get('print', False):
            reports = res.get('toolbar').get('print')
            for report in reports:
                res['toolbar']['print'].remove(report)
        return res

    @api.onchange('progressive_bill')
    def _onchange_progressive_bill(self):
        context = dict(self.env.context) or {}
        if context.get('progressive_bill'):
            self.progressive_bill = True

    @api.constrains('project_id', 'contract_parent', 'contract_parent_po')
    def _check_existing_record(self):
        for record in self:
            if record.progressive_bill == False:
                name_id = self.env['progressive.claim'].search(
                    [('project_id', '=', record.project_id.id), ('contract_parent', '=', record.contract_parent.id),
                     ('state', '!=', 'cancel')])
            else:
                name_id = self.env['progressive.claim'].search(
                    [('project_id', '=', record.project_id.id),
                     ('contract_parent_po', '=', record.contract_parent_po.id), ('state', '!=', 'cancel')])

            if len(name_id) > 1:
                if record.progressive_bill == False:
                    raise ValidationError(
                        _('The Progressive Claim with Project "%s" and Contract Parent "%s" is already exists. Please select another Project or another Contract Parent.' % (
                            (record.project_id.name), (record.contract_parent.name))))
                else:
                    raise ValidationError(
                        _('The Progressive Claim with Project "%s" and Contract Parent "%s" is already exists. Please select another Project or another Contract Parent.' % (
                            (record.project_id.name), (record.contract_parent_po.name))))

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            res = self.project_id
            self.project_director = res.project_director.id
            self.start_date = res.start_date
            self.end_date = res.end_date
            self.branch_id = res.branch_id.id
            if self.progressive_bill == False:
                self.partner_id = res.partner_id.id
                self.partner_invoice_id = res.partner_id.id
                self.analytic_idz = res.analytic_idz
            else:
                self.partner_id = False
                self.partner_invoice_id = False
                self.analytic_idz = False
        else:
            self.partner_id = False
            self.partner_invoice_id = False
            self.project_director = False
            self.analytic_idz = False
            self.start_date = False
            self.end_date = False
            self.contract_parent = False
            self.branch_id = False

    @api.onchange('contract_parent')
    def _onchange_contract_parent(self):
        if self.contract_parent:
            res = self.contract_parent
            self.dp_method = res.dp_method
            self.dp_amount = res.dp_amount
            self.down_payment = res.down_payment
            self.retention1 = res.retention1
            self.retention2 = res.retention2
            self.tax_id = [(6, 0, [v.id for v in res.tax_id])]
            self.payment_term = res.payment_term_id
            self.related_contract_so_ids = [(6, 0, [v.id for v in res.related_contract_ids])]

    @api.onchange('contract_parent_po')
    def _onchange_contract_parent_po(self):
        if self.contract_parent_po:
            res = self.contract_parent_po
            self.vendor = res.partner_id.id
            self.partner_bill_id = res.partner_id.id
            self.analytic_idz = res.analytic_account_group_ids
            self.dp_method = res.down_payment_method
            self.down_payment = res.down_payment
            self.dp_amount = res.dp_amount
            self.retention1 = res.retention_1
            self.retention2 = res.retention_2
            self.tax_id = [(6, 0, [v.id for v in res.tax_id])]
            self.payment_term = res.payment_term_id
            self.related_contract_po_ids = [(6, 0, [v.id for v in res.related_contract_ids])]

    @api.depends('related_contract_so_ids.contract_amount', 'related_contract_po_ids.discounted_total')
    def _compute_contract_amount(self):
        total = 0
        for res in self:
            if res.progressive_bill is False:
                if res.contract_parent and res.project_id:
                    # contract1 = self.env['sale.order.const'].search(
                    #     [('contract_parent', '=', res.contract_parent.id), ('project_id', '=', res.project_id.id),
                    #      ('state', 'in', ('sale', 'done'))])
                    # total1 = sum(contract1.mapped('contract_amount'))
                    # self.env.cr.execute("""
                    #     SELECT SUM(contract_amount1) FROM sale_order_const WHERE contract_parent = %s AND project_id = %s
                    #      AND state IN ('sale', 'done')
                    # """ % (res.contract_parent.id, res.project_id.id))
                    # query_result = self.env.cr.fetchall()
                    # if query_result:
                    #     total = query_result[0][0]
                    # else:
                    #     total = 0
                    for contract in res.related_contract_so_ids:
                        if contract.contract_category == 'main':
                            total += contract.contract_amount1
                        elif contract.contract_category == 'var' and contract.vo_payment_type == 'join':
                            total += contract.amount_total_variation_order
                else:
                    total = 0
                res.contract_amount = total
            else:
                if res.contract_parent_po and res.project_id:
                    # contract2 = self.env['purchase.order'].search(
                    #     [('is_subcontracting', '=', True), ('contract_parent_po', '=', res.contract_parent_po.id),
                    #      ('project', '=', res.project_id.id), ('state', 'in', ('purchase', 'done'))])
                    # total1 = sum(contract2.mapped('discounted_total'))
                    self.env.cr.execute("""
                        SELECT SUM(discounted_total) FROM purchase_order WHERE is_subcontracting = True AND contract_parent_po = %s
                            AND project = %s AND state IN ('purchase', 'done')
                    """ % (res.contract_parent_po.id, res.project_id.id))
                    query_result = self.env.cr.fetchall()
                    if query_result:
                        total = query_result[0][0]
                    else:
                        total = 0
                else:
                    total = 0

                res.contract_amount = total
        return total

    def _compute_count_contract_so(self):
        for res in self:
            contract = self.env['sale.order.const'].search_count(
                [('contract_parent', '=', res.contract_parent.id), ('project_id', '=', res.project_id.id),
                 ('state', 'in', ('sale', 'done'))])
            res.count_contract_so = contract

    def _compute_count_contract_po(self):
        for res in self:
            contract = self.env['purchase.order'].search_count(
                [('is_subcontracting', '=', True), ('contract_parent_po', '=', res.contract_parent_po.id),
                 ('project', '=', res.project_id.id), ('state', 'in', ('purchase', 'done'))])
            res.count_contract_po = contract

    def _compute_count_claim(self):
        for res in self:
            claim_so = self.env['project.claim'].search_count(
                [('claim_id', '=', res.id), ('contract_parent', '=', res.contract_parent.id)])
            claim_po = self.env['project.claim'].search_count(
                [('claim_id', '=', res.id), ('contract_parent_po', '=', res.contract_parent_po.id)])
            res.count_claim_so = claim_so
            res.count_claim_po = claim_po

    def create_request(self):
        context = {}
        if self.claim_request is True:
            if self.progressive_bill:
                if self.claim_type != 'milestone':
                    if self.approved_progress != self.invoiced_progress:
                        raise ValidationError(_("You can't create new claim request. Please create bill for your previous "
                                                "progress first."))
            context = {'default_request_for': 'progress',
                       'default_progressive_bill': self.progressive_bill,
                       'default_project_id': self.project_id.id or False,
                       'default_partner_id': self.partner_id.id or False,
                       'default_vendor': self.vendor.id or False,
                       'default_branch_id': self.branch_id.id or False,
                       'default_project_director': self.project_director.id or False,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_last_progress': self.approved_progress,
                       'default_progressive_claim_id': self.id,
                       'default_contract_parent': self.contract_parent.id or False,
                       'default_contract_parent_po': self.contract_parent_po.id or False,
                       }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'claim.request',
            'name': "Create Claim Request",
            "context": context,
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
        }

    def create_invoice_dp(self):
        # if self.is_set_custom_claim and self.claim_type == 'monthly':
        #     current_date = datetime.now()
        #     month_dict = {
        #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        #     }
        #     if self.repeat_on_month == "date":
        #         date = int(self.repeat_day)
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date).strftime('%d/%m/%Y')}"))

        #     elif self.repeat_on_month == "day":
        #         week_add_dict = {
        #             "first": 0, "second": 7, "third": 14, "last": 21
        #         }
        #         weekday_dict = {
        #             "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        #         }

        #         date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
        #         date_curr = dates_curr[date_num].day
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date_curr)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
        #                 date_next = dates_next[date_num].day
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date_next).strftime('%d/%m/%Y')}"))

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])
        const = self.env['project.claim'].search([('claim_id', '=', self.id), ('claim_for', '=', 'down_payment')])
        totgress = sum(const.mapped('progress'))
        totmount = sum(const.mapped('amount_untaxed'))

        context_unpaid = {'default_invoice_for': 'down_payment',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_last_progress': totgress,
                          'default_last_amount': totmount,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }
        # if self.is_set_custom_claim and self.claim_type == 'milestone':
        #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'down_payment'), ('is_invoiced', '=', False)], order="id asc", limit=1)
        #     if dp_milestones:
        #         context_unpaid['default_milestone_id'] = dp_milestones.id
        #         context_unpaid['default_invoiced_progress'] = dp_milestones.claim_percentage

        if self.dp_able == True:
            context = {'default_invoice_for': 'down_payment',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.dp_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_last_progress': totgress,
                       'default_last_amount': totmount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }
            # if self.is_set_custom_claim and self.claim_type == 'milestone':
            #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'down_payment'), ('is_invoiced', '=', False)], order="id asc", limit=1)
            #     if dp_milestones:
            #         context['default_milestone_id'] = dp_milestones.id
            #         context['default_invoice_progress'] = dp_milestones.claim_percentage

        if len(claim_id) == 0:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'progressive.invoice.wiz',
                'name': "Create Progressive Invoice",
                "context": context,
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
            }
        elif len(claim_id) > 0:
            if len(claim_id_unpaid) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Invoice",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id_unpaid) > 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'unpaid.confirmation.wiz',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    "context": context_unpaid
                }

    def create_bill_dp(self):
        # if self.is_set_custom_claim and self.claim_type == 'monthly':
        #     current_date = datetime.now()
        #     month_dict = {
        #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        #     }
        #     if self.repeat_on_month == "date":
        #         date = int(self.repeat_day)
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date).strftime('%d/%m/%Y')}"))
        #     elif self.repeat_on_month == "day":
        #         week_add_dict = {
        #             "first": 0, "second": 7, "third": 14, "last": 21
        #         }
        #         weekday_dict = {
        #             "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        #         }

        #         date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
        #         date_curr = dates_curr[date_num].day
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date_curr)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
        #                 date_next = dates_next[date_num].day
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date_next).strftime('%d/%m/%Y')}"))

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])
        const = self.env['project.claim'].search([('claim_id', '=', self.id), ('claim_for', '=', 'down_payment')])
        totgress = sum(const.mapped('progress'))
        totmount = sum(const.mapped('amount_untaxed'))

        context_unpaid = {'default_invoice_for': 'down_payment',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_last_progress': totgress,
                          'default_last_amount': totmount,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }
        # if self.is_set_custom_claim and self.claim_type == 'milestone':
        #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'down_payment'), ('is_invoiced', '=', False)], order="id asc", limit=1)
        #     if dp_milestones:
        #         context_unpaid['default_milestone_id'] = dp_milestones.id
        #         context_unpaid['default_invoiced_progress'] = dp_milestones.claim_percentage

        if self.dp_able == True:
            context = {'default_invoice_for': 'down_payment',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.dp_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_last_progress': totgress,
                       'default_last_amount': totmount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }

            # if self.is_set_custom_claim and self.claim_type == 'milestone':
            #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'down_payment'), ('is_invoiced', '=', False)], order="id asc", limit=1)
            #     if dp_milestones:
            #         context['default_milestone_id'] = dp_milestones.id
            #         context['default_invoice_progress'] = dp_milestones.claim_percentage

        if len(claim_id) == 0:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'progressive.invoice.wiz',
                'name': "Create Progressive Bill",
                "context": context,
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
            }
        elif len(claim_id) > 0:
            if len(claim_id_unpaid) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Bill",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id_unpaid) > 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'unpaid.confirmation.wiz',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    "context": context_unpaid
                }

    def _check_date(self, year, month, day):
        # Get Max value for a day in given month
        if month == 1 or month == 3 or month == 5 or month == 7 or month == 8 or month == 10 or month == 12:
            max_day_value = 31
        elif month == 4 or month == 6 or month == 9 or month == 11:
            max_day_value = 30
        elif year % 4 == 0 and year % 100 != 0 or year % 400 == 0:
            max_day_value = 29
        else:
            max_day_value = 28

        if month < 1 or month > 12:
            return False
        elif day < 1 or day > max_day_value:
            return max_day_value
        else:
            return day

    def create_invoice_progress(self):
        if self.is_set_custom_claim and self.claim_type == 'monthly':
            current_date = datetime.now()
            if self.repeat_on_month == "date":

                current_month = (current_date + timedelta(hours=7)).month
                current_year = (current_date + timedelta(hours=7)).year
                date = self._check_date(current_year, current_month, int(self.repeat_day))

                force_create = self._context.get('force_create_invoice_progress', False)
                if (current_date + timedelta(hours=7)) < datetime(current_year, current_month,
                                                                  date) and not force_create:
                    raise ValidationError(_("You can create an invoice for this month on %s.") % datetime(current_year, current_month, date).strftime('%d/%m/%Y'))
                else:
                    invoice = self.env['account.move'].search(
                        [('claim_id', '=', self.id), ('progressive_method', '=', 'progress'),
                         ('create_date', '>=', datetime(current_year, current_month, date) - timedelta(hours=7))])
                    if len(invoice) > 0:
                        next_month = current_month + 1
                        next_year = current_year
                        if next_month > 12:
                            next_month -= 12
                            next_year += 1

                        for history in self.claim_ids:
                            if history.claim_for == 'progress':
                                history_month = (history.create_date + timedelta(hours=7)).month
                                history_year = (history.create_date + timedelta(hours=7)).year
                                if history.invoice_id.create_date >= datetime(current_year, current_month,
                                                                              date) - timedelta(
                                    hours=7) and history_month == current_month and history_year == current_year:
                                    if not force_create:
                                        if self.progressive_bill:
                                            raise ValidationError(_("You have already created a bill for this month. You can create a bill in the next month on %s.") % datetime(next_year, next_month, date).strftime('%d/%m/%Y'))
                                        else:
                                            raise ValidationError(_("You have already created an invoice for this month. You can create an invoice in the next month on %s.") % datetime(next_year, next_month, date).strftime('%d/%m/%Y'))
            
            elif self.repeat_on_month == "day":
                week_add_dict = {
                    "first": 0, "second": 7, "third": 14, "last": 21
                }
                weekday_dict = {
                    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
                }
                date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
                current_month = (current_date + timedelta(hours=7)).month
                current_year = (current_date + timedelta(hours=7)).year
                dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
                date_curr = dates_curr[date_num].day
                if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
                    raise ValidationError(_("You can create an invoice for this month on %s.") % datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y'))
                else:
                    invoice = self.env['account.move'].search(
                        [('claim_id', '=', self.id), ('progressive_method', '=', 'progress'),
                         ('create_date', '>=', datetime(current_year, current_month, date_curr) - timedelta(hours=7))])
                    if len(invoice) > 0:
                        next_month = current_month + 1
                        next_year = current_year
                        if next_month > 12:
                            next_month -= 12
                            next_year += 1
                        dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
                        date_next = dates_next[date_num].day
                        raise ValidationError(_("You have already created an invoice for this month. You can create an invoice in the next month on %s.") % datetime(next_year, next_month, date_next).strftime('%d/%m/%Y'))

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])
        const = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progressline', '=', self.invoiced_progress)],
            limit=1)
        tot = sum(const.mapped('gross_amount'))

        context_unpaid = {'default_invoice_for': 'progress',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_last_progress': self.invoiced_progress,
                          'default_last_amount': tot,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }
        if self.is_set_custom_claim and self.claim_type == 'milestone':
            dp_milestones = self.env['account.milestone.term.const'].search(
                [('claim_id', '=', self.id), ('type_milestone', '=', 'progress'), ('is_invoiced', '=', False)],
                order="id asc", limit=1)
            if dp_milestones:
                invoice_progress = dp_milestones.claim_percentage
                if self.approved_progress < invoice_progress:
                    raise ValidationError(_("The Approved Progress is less than %s%%, it hasn't reached the target of %s") % (invoice_progress, dp_milestones.name))

                context_unpaid['default_milestone_id'] = dp_milestones.id
                # context_unpaid['default_invoiced_progress'] = dp_milestones.claim_percentage

        if self.invoiceable_progress == True:
            context = {'default_invoice_for': 'progress',
                       'default_progressive_bill': self.progressive_bill,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_last_progress': self.invoiced_progress,
                       'default_last_amount': tot,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }
            if self.is_set_custom_claim and self.claim_type == 'milestone':
                dp_milestones = self.env['account.milestone.term.const'].search(
                    [('claim_id', '=', self.id), ('type_milestone', '=', 'progress'), ('is_invoiced', '=', False)],
                    order="id asc", limit=1)
                if dp_milestones:
                    invoice_progress = dp_milestones.claim_percentage
                    if self.approved_progress < invoice_progress:
                        raise ValidationError(_("The Approved Progress is less than %s%%, it hasn't reached the target of %s") % (invoice_progress, dp_milestones.name))

                    context['default_milestone_id'] = dp_milestones.id
                    # context['default_invoiced_progress'] = dp_milestones.claim_percentage

        if len(claim_id) == 0:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'progressive.invoice.wiz',
                'name': "Create Progressive Invoice",
                "context": context,
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
            }
        elif len(claim_id) > 0:
            if len(claim_id_unpaid) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Invoice",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id_unpaid) > 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'unpaid.confirmation.wiz',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    "context": context_unpaid
                }

    def create_bill_progress(self):
        if self.is_set_custom_claim and self.claim_type == 'monthly':
            current_date = datetime.now()
            if self.repeat_on_month == "date":
                current_month = (current_date + timedelta(hours=7)).month
                current_year = (current_date + timedelta(hours=7)).year
                date = self._check_date(current_year, current_month, int(self.repeat_day))

                force_create = self._context.get('force_create_invoice_progress', False)
                if (current_date + timedelta(hours=7)) < datetime(current_year, current_month,
                                                                  date) and not force_create:
                    raise ValidationError(_("You can create bill for this month on %s.") % datetime(current_year, current_month, date).strftime('%d/%m/%Y'))
                else:
                    invoice = self.env['account.move'].search(
                        [('claim_id', '=', self.id), ('progressive_method', '=', 'progress'),
                         ('create_date', '>=', datetime(current_year, current_month, date) - timedelta(hours=7))])
                    if len(invoice) > 0:
                        next_month = current_month + 1
                        next_year = current_year
                        if next_month > 12:
                            next_month -= 12
                            next_year += 1

                        for history in self.claim_ids:
                            if history.claim_for == 'progress':
                                history_month = (history.create_date + timedelta(hours=7)).month
                                history_year = (history.create_date + timedelta(hours=7)).year
                                if history.invoice_id.create_date >= datetime(current_year, current_month,
                                                                              date) - timedelta(
                                    hours=7) and history_month == current_month and history_year == current_year:
                                    if not force_create:
                                        if self.progressive_bill:
                                            raise ValidationError(_("You have already created a bill for this month. You can create a bill in the next month on %s.") % datetime(next_year, next_month, date).strftime('%d/%m/%Y'))
                                        else:
                                            raise ValidationError(
                                                _("You have already create invoice for this month. You can create invoice in the next month on %s.") % datetime(next_year, next_month, date).strftime('%d/%m/%Y'))
                            
            elif self.repeat_on_month == "day":
                week_add_dict = {
                    "first": 0, "second": 7, "third": 14, "last": 21
                }
                weekday_dict = {
                    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
                }
                date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
                current_month = (current_date + timedelta(hours=7)).month
                current_year = (current_date + timedelta(hours=7)).year
                dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
                date_curr = dates_curr[date_num].day
                if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
                    raise ValidationError(
                        _("You can create invoice for this month on %s.") % datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y'))
                else:
                    invoice = self.env['account.move'].search(
                        [('claim_id', '=', self.id), ('progressive_method', '=', 'progress'),
                         ('create_date', '>=', datetime(current_year, current_month, date_curr) - timedelta(hours=7))])
                    if len(invoice) > 0:
                        next_month = current_month + 1
                        next_year = current_year
                        if next_month > 12:
                            next_month -= 12
                            next_year += 1
                        dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
                        date_next = dates_next[date_num].day
                        raise ValidationError(
                            _("You have already create invoice for this month. You can create invoice in the next month on .") % datetime(next_year, next_month, date_next).strftime('%d/%m/%Y'))

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])
        const = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progressline', '=', self.invoiced_progress)],
            limit=1)
        tot = sum(const.mapped('gross_amount'))

        context_unpaid = {'default_invoice_for': 'progress',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_last_progress': self.invoiced_progress,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }

        if self.is_set_custom_claim and self.claim_type == 'milestone':
            progress_milestones = self.env['account.milestone.term.const'].search(
                [('claim_id', '=', self.id), ('type_milestone', '=', 'progress'), ('is_invoiced', '=', False)],
                order="id asc", limit=1)
            if progress_milestones:
                invoice_progress = progress_milestones.claim_percentage
                if self.approved_progress < invoice_progress:
                    raise ValidationError(
                        _("The Approved Progress is less than %s%%, it hasn't reached the target of %s.") % (invoice_progress, progress_milestones.name))

                context_unpaid['default_milestone_id'] = progress_milestones.id
                # context_unpaid['default_invoiced_progress'] = progress_milestones.claim_percentage

        if self.invoiceable_progress == True:
            context = {'default_invoice_for': 'progress',
                       'default_progressive_bill': self.progressive_bill,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_last_progress': self.invoiced_progress,
                       'default_down_payment': self.down_payment,
                       'default_last_amount': tot,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }

            if self.is_set_custom_claim and self.claim_type == 'milestone':
                progress_milestones = self.env['account.milestone.term.const'].search(
                    [('claim_id', '=', self.id), ('type_milestone', '=', 'progress'), ('is_invoiced', '=', False)],
                    order="id asc", limit=1)
                if progress_milestones:
                    invoice_progress = progress_milestones.claim_percentage
                    if self.approved_progress < invoice_progress:
                        raise ValidationError(
                            _("The Approved Progress is less than %s%%, it hasn't reached the target of %s.") % (invoice_progress, progress_milestones.name))

                    context['default_milestone_id'] = progress_milestones.id
                    # context['default_invoice_progress'] = progress_milestones.claim_percentage

        if len(claim_id) == 0:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'progressive.invoice.wiz',
                'name': "Create Progressive Bill",
                "context": context,
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
            }
        elif len(claim_id) > 0:
            if len(claim_id_unpaid) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Bill",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id_unpaid) > 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'unpaid.confirmation.wiz',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    "context": context_unpaid
                }

    def create_invoice_retention1(self):
        # if self.is_set_custom_claim and self.claim_type == 'monthly':
        #     current_date = datetime.now()
        #     if self.repeat_on_month == "date":
        #         date = int(self.repeat_day)
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date).strftime('%d/%m/%Y')}"))
        #     elif self.repeat_on_month == "day":
        #         week_add_dict = {
        #             "first": 0, "second": 7, "third": 14, "last": 21
        #         }
        #         weekday_dict = {
        #             "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        #         }
        #         date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
        #         date_curr = dates_curr[date_num].day
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date_curr)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
        #                 date_next = dates_next[date_num].day
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date_next).strftime('%d/%m/%Y')}"))

        contract = self.contract_parent
        retention_term = contract.retention_term_1
        day_term = retention_term.days

        if self.complete_progress == False:
            full_progress = self.env['project.claim'].search(
                [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progressline', '=', 100)], limit=1)
        else:
            full_progress = self.env['project.claim'].search([('claim_id', '=', self.id)], limit=1,
                                                             order='create_date desc')

        date_progress = full_progress.date
        invoice_date = date_progress + relativedelta(days=+(day_term))

        current_day = (invoice_date).day
        current_month = (invoice_date).month
        current_year = (invoice_date).year

        date_now = date.today()

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])

        context_unpaid = {'default_invoice_for': 'retention1',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }

        # if self.is_set_custom_claim and self.claim_type == 'milestone':
        #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention1'), ('is_invoiced', '=', False)], order="id asc", limit=1)
        #     if dp_milestones:
        #         context_unpaid['default_milestone_id'] = dp_milestones.id
        #         context_unpaid['default_invoiced_progress'] = dp_milestones.claim_percentage

        if self.progress_full_invoiced or self.complete_progress:
            context = {'default_invoice_for': 'retention1',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.retention1_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }
            # if self.is_set_custom_claim and self.claim_type == 'milestone':
            #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention1'), ('is_invoiced', '=', False)], order="id asc", limit=1)
            #     if dp_milestones:
            #         context['default_milestone_id'] = dp_milestones.id
            #         context['default_invoice_progress'] = dp_milestones.claim_percentage

        if date_now < invoice_date:
            if self.project_id.flexible_reten == True:
                if len(claim_id_unpaid) == 0:
                    reten_context = context
                elif len(claim_id_unpaid) > 0:
                    reten_context = context_unpaid

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'retention.claim.confirmation.wiz',
                    'name': "Confirmation",
                    "context": reten_context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            else:
                raise ValidationError(
                    _("Retention 1 cannot be invoiced. You can create this invoice on %s.") % datetime(current_year, current_month, current_day).strftime('%d/%m/%Y'))
        else:
            if len(claim_id) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Bill",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id) > 0:
                if len(claim_id_unpaid) == 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'progressive.invoice.wiz',
                        'name': "Create Progressive Bill",
                        "context": context,
                        'target': 'new',
                        'view_type': 'form',
                        'view_mode': 'form',
                    }
                elif len(claim_id_unpaid) > 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'unpaid.confirmation.wiz',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                        "context": context_unpaid
                    }

    def create_bill_retention1(self):
        # if self.is_set_custom_claim and self.claim_type == 'monthly':
        #     current_date = datetime.now()
        #     if self.repeat_on_month == "date":
        #         date = int(self.repeat_day)
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date).strftime('%d/%m/%Y')}"))
        #     elif self.repeat_on_month == "day":
        #         week_add_dict = {
        #             "first": 0, "second": 7, "third": 14, "last": 21
        #         }
        #         weekday_dict = {
        #             "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        #         }

        #         date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
        #         date_curr = dates_curr[date_num].day
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date_curr)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
        #                 date_next = dates_next[date_num].day
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date_next).strftime('%d/%m/%Y')}"))

        contract = self.contract_parent_po
        retention_term = contract.retention_term_1
        day_term = retention_term.days

        if self.complete_progress == False:
            full_progress = self.env['project.claim'].search(
                [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progressline', '=', 100)], limit=1)
        else:
            full_progress = self.env['project.claim'].search([('claim_id', '=', self.id)], limit=1,
                                                             order='create_date desc')

        date_progress = full_progress.date
        invoice_date = date_progress + relativedelta(days=+(day_term))

        current_day = (invoice_date).day
        current_month = (invoice_date).month
        current_year = (invoice_date).year

        date_now = date.today()

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])

        context_unpaid = {'default_invoice_for': 'retention1',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }

        # if self.is_set_custom_claim and self.claim_type == 'milestone':
        #     retention_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention2'), ('is_invoiced', '=', False)], order="id asc", limit=1)
        #     if retention_milestones:
        #         context_unpaid['default_milestone_id'] = retention_milestones.id
        #         context_unpaid['default_invoiced_progress'] = retention_milestones.claim_percentage

        if self.progress_full_invoiced or self.complete_progress:
            context = {'default_invoice_for': 'retention1',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.retention1_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }
            # if self.is_set_custom_claim and self.claim_type == 'milestone':
            #     retention_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention2'), ('is_invoiced', '=', False)], order="id asc", limit=1)
            #     if retention_milestones:
            #         context['default_milestone_id'] = retention_milestones.id
            #         context['default_invoice_progress'] = retention_milestones.claim_percentage

        if date_now < invoice_date:
            if self.project_id.flexible_reten == True:
                if len(claim_id_unpaid) == 0:
                    reten_context = context
                elif len(claim_id_unpaid) > 0:
                    reten_context = context_unpaid

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'retention.claim.confirmation.wiz',
                    'name': "Confirmation",
                    "context": reten_context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            else:
                raise ValidationError(
                    _("Retention 1 cannot be billed. You can create this bill on %s.") % datetime(current_year, current_month, current_day).strftime('%d/%m/%Y'))
        else:
            if len(claim_id) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Bill",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id) > 0:
                if len(claim_id_unpaid) == 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'progressive.invoice.wiz',
                        'name': "Create Progressive Bill",
                        "context": context,
                        'target': 'new',
                        'view_type': 'form',
                        'view_mode': 'form',
                    }
                elif len(claim_id_unpaid) > 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'unpaid.confirmation.wiz',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                        "context": context_unpaid
                    }

    def create_invoice_retention2(self):
        # if self.is_set_custom_claim and self.claim_type == 'monthly':
        #     current_date = datetime.now()
        #     if self.repeat_on_month == "date":
        #         date = int(self.repeat_day)
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date).strftime('%d/%m/%Y')}"))
        #     elif self.repeat_on_month == "day":
        #         week_add_dict = {
        #             "first": 0, "second": 7, "third": 14, "last": 21
        #         }
        #         weekday_dict = {
        #             "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        #         }
        #         date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
        #         date_curr = dates_curr[date_num].day
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date_curr)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
        #                 date_next = dates_next[date_num].day
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date_next).strftime('%d/%m/%Y')}"))

        contract = self.contract_parent
        retention_term = contract.retention_term_2
        day_term = retention_term.days

        retention_1 = self.env['project.claim'].search([('claim_id', '=', self.id), ('claim_for', '=', 'retention1')],
                                                       limit=1)

        date_progress = retention_1.date
        invoice_date = date_progress + relativedelta(days=+(day_term))

        current_day = (invoice_date).day
        current_month = (invoice_date).month
        current_year = (invoice_date).year

        date_now = date.today()

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])

        context_unpaid = {'default_invoice_for': 'retention2',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }

        # if self.is_set_custom_claim and self.claim_type == 'milestone':
        #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention2'), ('is_invoiced', '=', False)], order="id asc", limit=1)
        #     if dp_milestones:
        #         context_unpaid['default_milestone_id'] = dp_milestones.id
        #         context_unpaid['default_invoiced_progress'] = dp_milestones.claim_percentage

        if self.progress_full_invoiced or self.complete_progress:
            context = {'default_invoice_for': 'retention2',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.retention2_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }
            # if self.is_set_custom_claim and self.claim_type == 'milestone':
            #     dp_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention2'), ('is_invoiced', '=', False)], order="id asc", limit=1)
            #     if dp_milestones:
            #         context['default_milestone_id'] = dp_milestones.id
            #         context['default_invoice_progress'] = dp_milestones.claim_percentage

        if date_now < invoice_date:
            if self.project_id.flexible_reten == True:
                if len(claim_id_unpaid) == 0:
                    reten_context = context
                elif len(claim_id_unpaid) > 0:
                    reten_context = context_unpaid

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'retention.claim.confirmation.wiz',
                    'name': "Confirmation",
                    "context": reten_context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            else:
                raise ValidationError(
                    _("Retention 2 cannot be invoiced. You can create this invoice on %s.") % datetime(current_year, current_month, current_day).strftime('%d/%m/%Y'))
        else:
            if len(claim_id) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Invoice",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id) > 0:
                if len(claim_id_unpaid) == 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'progressive.invoice.wiz',
                        'name': "Create Progressive Invoice",
                        "context": context,
                        'target': 'new',
                        'view_type': 'form',
                        'view_mode': 'form',
                    }
                elif len(claim_id_unpaid) > 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'unpaid.confirmation.wiz',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                        "context": context_unpaid
                    }

    def create_bill_retention2(self):
        # if self.is_set_custom_claim and self.claim_type == 'monthly':
        #     current_date = datetime.now()
        #     if self.repeat_on_month == "date":
        #         date = int(self.repeat_day)
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date).strftime('%d/%m/%Y')}"))
        #     elif self.repeat_on_month == "day":
        #         week_add_dict = {
        #             "first": 0, "second": 7, "third": 14, "last": 21
        #         }
        #         weekday_dict = {
        #             "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        #         }
        #         date_num = week_add_dict[self.repeat_week] + weekday_dict[self.repeat_weekday]
        #         current_month = (current_date + timedelta(hours=7)).month
        #         current_year = (current_date + timedelta(hours=7)).year
        #         dates_curr = [d for d in Calendar(6).itermonthdates(current_year, current_month)]
        #         date_curr = dates_curr[date_num].day
        #         if (current_date + timedelta(hours=7)) < datetime(current_year, current_month, date_curr):
        #             raise ValidationError(_(f"You can create invoice for this month on {datetime(current_year, current_month, date_curr).strftime('%d/%m/%Y')}"))
        #         else:
        #             invoice = self.env['account.move'].search([('claim_id', '=', self.id), ('create_date', '>=', datetime(current_year, current_month, date_curr)-timedelta(hours=7))])
        #             if len(invoice) > 0:
        #                 next_month = current_month + 1
        #                 next_year = current_year
        #                 if next_month > 12:
        #                     next_month -= 12
        #                     next_year += 1
        #                 dates_next = [d for d in Calendar(6).itermonthdates(next_year, next_month)]
        #                 date_next = dates_next[date_num].day
        #                 raise ValidationError(_(f"You have already create invoice for this month. You can create invoice in the next month on {datetime(next_year, next_month, date_next).strftime('%d/%m/%Y')}"))

        contract = self.contract_parent_po
        retention_term = contract.retention_term_2
        day_term = retention_term.days

        retention_1 = self.env['project.claim'].search([('claim_id', '=', self.id), ('claim_for', '=', 'retention1')],
                                                       limit=1)

        date_progress = retention_1.date
        invoice_date = date_progress + relativedelta(days=+(day_term))

        current_day = (invoice_date).day
        current_month = (invoice_date).month
        current_year = (invoice_date).year

        date_now = date.today()

        claim_id = self.env['project.claim'].search([('claim_id', '=', self.id)])
        claim_id_unpaid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('payment_status', '!=', 'paid')])

        context_unpaid = {'default_invoice_for': 'retention2',
                          'default_progressive_bill': self.progressive_bill,
                          'default_invoiced_progress': self.invoiced_progress,
                          'default_approved_progress': self.approved_progress,
                          'default_contract_amount': self.contract_amount,
                          'default_down_payment': self.down_payment,
                          'default_dp_amount': self.dp_amount,
                          'default_retention1': self.retention1,
                          'default_retention2': self.retention2,
                          'default_retention1_amount': self.retention1_amount,
                          'default_retention2_amount': self.retention2_amount,
                          'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                          'default_progressive_claim_id': self.id,
                          }
        # if self.is_set_custom_claim and self.claim_type == 'milestone':
        #     retention_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention1'), ('is_invoiced', '=', False)], order="id asc", limit=1)
        #     if retention_milestones:
        #         context_unpaid['default_milestone_id'] = retention_milestones.id
        #         context_unpaid['default_invoiced_progress'] = retention_milestones.claim_percentage

        if self.progress_full_invoiced or self.complete_progress:
            context = {'default_invoice_for': 'retention2',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.retention2_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment': self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.id,
                       }
            # if self.is_set_custom_claim and self.claim_type == 'milestone':
            #     retention_milestones = self.env['account.milestone.term.const'].search([('claim_id', '=', self.id), ('type_milestone', '=', 'retention1'), ('is_invoiced', '=', False)], order="id asc", limit=1)
            #     if retention_milestones:
            #         context['default_milestone_id'] = retention_milestones.id
            #         context['default_invoice_progress'] = retention_milestones.claim_percentage

        if date_now < invoice_date:
            if self.project_id.flexible_reten == True:
                if len(claim_id_unpaid) == 0:
                    reten_context = context
                elif len(claim_id_unpaid) > 0:
                    reten_context = context_unpaid

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'retention.claim.confirmation.wiz',
                    'name': "Confirmation",
                    "context": reten_context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            else:
                raise ValidationError(
                    _("Retention 2 cannot be billed. You can create this bill on %s.") % datetime(current_year, current_month, current_day).strftime('%d/%m/%Y'))
        else:
            if len(claim_id) == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progressive.invoice.wiz',
                    'name': "Create Progressive Bill",
                    "context": context,
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                }
            elif len(claim_id) > 0:
                if len(claim_id_unpaid) == 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'progressive.invoice.wiz',
                        'name': "Create Progressive Bill",
                        "context": context,
                        'target': 'new',
                        'view_type': 'form',
                        'view_mode': 'form',
                    }
                elif len(claim_id_unpaid) > 0:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'unpaid.confirmation.wiz',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                        "context": context_unpaid
                    }

    def _compute_expected_retention(self):
        if self.progressive_bill == False:
            contract = self.contract_parent
        else:
            contract = self.contract_parent_po

        retention_term_1 = contract.retention_term_1
        day_term_1 = retention_term_1.days

        retention_term_2 = contract.retention_term_2
        day_term_2 = retention_term_2.days

        if self.retention1 > 0:
            if self.invoiceable_rent1 == True:
                if self.complete_progress == False:
                    full_progress = self.env['project.claim'].search(
                        [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progressline', '=', 100)],
                        limit=1)
                else:
                    full_progress = self.env['project.claim'].search([('claim_id', '=', self.id)], limit=1,
                                                                     order='create_date desc')

                date_progress = full_progress.date

                expected_date_1 = date_progress + relativedelta(days=+(day_term_1))
                expected_date_2 = date_progress + relativedelta(days=+(day_term_1 + day_term_2))

                current_year_1 = expected_date_1.year
                current_month_1 = expected_date_1.month
                current_day_1 = expected_date_1.day

                current_year_2 = expected_date_2.year
                current_month_2 = expected_date_2.month
                current_day_2 = expected_date_2.day

                self.expected_retention1 = datetime(current_year_1, current_month_1, current_day_1).strftime('%d/%m/%Y')

                if self.retention2 > 0:
                    self.expected_retention2 = datetime(current_year_2, current_month_2, current_day_2).strftime(
                        '%d/%m/%Y')
                else:
                    self.expected_retention2 = False
            else:
                self.expected_retention1 = False
                self.expected_retention2 = False
        else:
            self.expected_retention1 = False
            self.expected_retention2 = False

    # def _compute_expected_retention1(self):
    #     contract = self.contract_parent
    #     retention_term = contract.retention_term_1
    #     day_term = retention_term.days
    #     date_progress = datetime.now()
    #     expected_date = date_progress + relativedelta(days=+(day_term))
    #     current_year = expected_date.year
    #     current_month = expected_date.month
    #     current_day = expected_date.day
    #     for rec in self:
    #         rec.expected_retention1 = datetime(current_year, current_month, current_day).strftime('%d/%m/%Y')

    # def _compute_expected_retention2(self):
    #     contract = self.contract_parent
    #     retention_term = contract.retention_term_2
    #     day_term = retention_term.days
    #     date_progress = datetime.now()
    #     expected_date = date_progress + relativedelta(days=+(day_term))
    #     current_year = expected_date.year
    #     current_month = expected_date.month
    #     current_day = expected_date.day
    #     for rec in self:
    #         if day_term > 0:
    #             rec.expected_retention2 = datetime(current_year, current_month, current_day).strftime('%d/%m/%Y')
    #         else:
    #             rec.expected_retention2 = rec.expected_retention1

    def claim_confirm(self):
        res = self.write({'state': 'in_progress'})

        if self.claim_type == "milestone":
            dp_to_invoiced = False
            ct = 101
            for m in self.milestone_term_ids:
                if m.type_milestone == "down_payment":
                    if m.claim_percentage < ct:
                        ct = m.claim_percentage
                        dp_to_invoiced = m
            if dp_to_invoiced != False:
                template_id = self.env.ref(
                    'equip3_construction_accounting_operation.email_template_reminder_milestone_create_invoice')
                if self.progressive_bill == False:
                    action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
                else:
                    action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

                for user in self.project_id.notification_claim:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url = base_url + '/web#id=' + str(self.id) + '&action=' + str(
                        action_id.id) + '&view_type=form&model=progressive.claim'
                    ctx = {
                        'email_from': self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                        'email_to': user.partner_id.email,
                        'approver_name': user.partner_id.name,
                        'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                        'url': url,
                        'next_milestone': dp_to_invoiced.name,
                        'invoice_for': "Progress"
                    }
                    template_id.sudo().with_context(ctx).send_mail(self.id, True)

        return res

    def reset_draft(self):
        res = self.write({'state': 'in_progress'})
        return res

    def action_cancel(self):
        # res = self.write({'state':'cancel'})
        context = {'default_progressive_bill': self.progressive_bill,
                   'default_contract_parent': self.contract_parent.id,
                   'default_contract_parent_po': self.contract_parent_po.id,
                   'default_progressive_claim_id': self.id
                   }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Confirmation',
            'res_model': 'cancel.claim.conf.wiz',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }

    def action_print_progressive_claim(self):
        for rec in self:
            return self.env.ref(
                'equip3_construction_accounting_operation.action_report_construction_progressive').report_action(rec)

    def action_done(self):
        all_claim = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('invoice_status', 'not in', ['rejected', 'cancel'])])
        all_claim_paid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('invoice_status', 'not in', ['rejected', 'cancel']),
             ('payment_status', '=', 'paid')])
        progress_done = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progress', '=', 100),
             ('payment_status', '=', 'paid')])
        retention_1 = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'retention1'), ('payment_status', '=', 'paid')])
        retention_2 = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'retention2'), ('payment_status', '=', 'paid')])
        for rec in self:
            if rec.retention1 == 0 and rec.retention2 == 0:
                if len(progress_done) == 0 or len(all_claim) != len(all_claim_paid):
                    raise ValidationError(
                        _('You have an unfinished progressive. Progressive claim is completed when the full progress has been paid.\nPlease continue the ongoing claim.'))
                elif len(progress_done) == 1 and len(all_claim) == len(all_claim_paid):
                    rec.write({'state': 'done'})
                    if rec.progressive_bill == False:
                        for contract in rec.related_contract_so_ids:
                            contract.write({'state': 'done'})
                    else:
                        for contract in rec.related_contract_po_ids:
                            contract.write({'state': 'done'})
            elif rec.retention1 != 0 and rec.retention2 == 0:
                if len(retention_1) == 0 or len(all_claim) != len(all_claim_paid):
                    raise ValidationError(
                        _('You have an unfinished progressive claim. Progressive claim is completed when the agreed retention has been paid.\nPlease continue the ongoing claim.'))
                elif len(retention_1) == 1 and len(all_claim) == len(all_claim_paid):
                    rec.write({'state': 'done'})
                    if rec.progressive_bill == False:
                        for contract in rec.related_contract_so_ids:
                            contract.write({'state': 'done'})
                    else:
                        for contract in rec.related_contract_po_ids:
                            contract.write({'state': 'done'})
            elif rec.retention1 != 0 and rec.retention2 != 0:
                if len(retention_2) == 0 or len(all_claim) != len(all_claim_paid):
                    raise ValidationError(
                        _('You have an unfinished progressive claim. Progressive claim is completed when the agreed retention has been paid.\nPlease continue the ongoing claim.'))
                elif len(retention_2) == 1 and len(all_claim) == len(all_claim_paid):
                    rec.write({'state': 'done'})
                    if rec.progressive_bill == False:
                        for contract in rec.related_contract_so_ids:
                            contract.write({'state': 'done'})
                    else:
                        for contract in rec.related_contract_po_ids:
                            contract.write({'state': 'done'})

    # def _get_cost_sheet(self):
    #     self.ensure_one()
    #     cost_sheet = self.env['job.cost.sheet'].search([('project_id', '=', self.project_id.id)])
    #     parent_contract = None

    #     if self.progressive_bill == False:
    #         parent_contract = self.contract_parent
    #     else:
    #         parent_contract = self.contract_parent_po

    #     if cost_sheet:
    #         for sheet in cost_sheet:
    #             for contract in sheet.contract_history_ids:
    #                 if contract.contract_history == parent_contract:
    #                     return sheet.number
    #     return False

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.onchange('claim_ids')
    def onchange_done(self):
        all_claim = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('invoice_status', 'not in', ['rejected', 'cancel'])])
        all_claim_paid = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('invoice_status', 'not in', ['rejected', 'cancel']),
             ('payment_status', '=', 'paid')])
        progress_done = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'progress'), ('progress', '=', 100),
             ('payment_status', '=', 'paid')])
        retention_1 = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'retention1'), ('payment_status', '=', 'paid')])
        retention_2 = self.env['project.claim'].search(
            [('claim_id', '=', self.id), ('claim_for', '=', 'retention2'), ('payment_status', '=', 'paid')])
        for rec in self:
            if rec.retention1 == 0 and rec.retention2 == 0:
                if len(progress_done) == 1 and len(all_claim) == len(all_claim_paid):
                    rec.write({'state': 'done'})
            elif rec.retention1 != 0 and rec.retention2 == 0:
                if len(retention_1) == 1 and len(all_claim) == len(all_claim_paid):
                    rec.write({'state': 'done'})
            elif rec.retention2 != 0:
                if len(retention_2) == 1 and len(all_claim) == len(all_claim_paid):
                    rec.write({'state': 'done'})

    @api.depends('retention1', 'contract_amount')
    def _compute_total_retention1(self):
        for res in self:
            res.retention1_amount = res.contract_amount * (res.retention1 / 100)

    @api.depends('retention2', 'contract_amount')
    def _compute_total_retention2(self):
        for res in self:
            res.retention2_amount = res.contract_amount * (res.retention2 / 100)

    @api.constrains('start_date', 'end_date')
    def constrains_date(self):
        for rec in self:
            if rec.start_date != False and rec.end_date != False:
                if rec.start_date > rec.end_date:
                    raise UserError(_('End date should be after start date.'))

    @api.depends('claim_ids')
    def _compute_count_invoices(self):
        for rec in self:
            account_moves = self.env['account.move'].search([('claim_id', '=', rec.id)], order='create_date')
            if account_moves:
                rec.count_invoice = len(account_moves.filtered(lambda x: x.move_type == 'out_invoice'))
                rec.count_bill = len(account_moves.filtered(lambda x: x.move_type == 'in_invoice'))

                filtered_claim_ids = rec.claim_ids.filtered(
                    lambda x: x.claim_for == 'progress' and not (x.invoice_status in ['rejected', 'cancel']))
                rec.invoiced_progress = sum(filtered_claim_ids.mapped('progress'))
            else:
                rec.count_invoice = 0
                rec.count_bill = 0
                rec.invoiced_progress = 0

    def create_claim_history(self):
        for rec in self:
            def _get_history_lines_vals(inv_ids):
                vals = []
                if len(inv_ids) > 0:
                    for inv in inv_ids:
                        val = {
                            'invoice_id': inv.id
                        }
                        vals.append((0, 0, val))
                if len(vals) > 0:
                    rec.claim_ids = False
                return vals

            def _compute_Invoiced_progress(self):
                total = 0
                for res in self:
                    cont = self.env['project.claim'].search([('claim_id', '=', res.id), ('claim_for', '=', 'progress'),
                                                             ('invoice_status', 'not in', ['rejected', 'cancel'])])
                    total = sum(cont.mapped('progress'))
                    res.invoiced_progress = total
                return total

            total = 0
            history_lines = False
            inv_ids = self.env['account.move'].search([('claim_id', '=', rec.id)], order='create_date')
            get_history_lines = _get_history_lines_vals(inv_ids)

            if len(inv_ids) > 0:
                total += len(inv_ids)
            if len(get_history_lines) > 0:
                history_lines = get_history_lines

            # Prevent CR invoices to be included inside claim_ids (this only happen on force create invoice)
            if history_lines:
                crj_invoice = self.env['account.move'].search(
                    [('claim_id', '=', rec.id), ('journal_id.code', '=', 'CRJ')])
                for history in history_lines:
                    if history[2]['invoice_id'] in crj_invoice.ids:
                        history_lines.remove(history)

            rec.claim_ids = history_lines
            rec.invoiced_progress = _compute_Invoiced_progress(self)

    def _count_perc(self, total_purchased):
        for rec in self:
            parent_cont = self.env['purchase.order'].search([('id', '=', rec.contract_parent_po.id)])
            for po in parent_cont:
                if total_purchased != 0 and rec.contract_amount != 0:
                    claim_perc = (total_purchased / rec.contract_amount) * 100
                    po.progressive_perc(claim_perc)

    def action_view_invoice(self):
        inv_ids = self.env['account.move'].search([('claim_id', '=', self.id)], order='id desc').ids
        domain_ids = [('id', 'in', inv_ids)]
        tree_view = self.env.ref('equip3_construction_accounting_operation.account_move_progressive_view_tree').id
        if len(inv_ids) < 1:
            domain_ids = [('id', '=', False)]
        action = {
            "name": _("Progressive Invoices") if self.progressive_bill is False else _("Progressive Bills"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "views": [(tree_view, "tree"), (False, "form")],
            "domain": domain_ids,
        }
        return action

    @api.constrains('progressive_bill')
    def contract_progressive_bill(self):
        if self.progressive_bill == True:
            self.name = self.env['ir.sequence'].next_by_code('progressive.project.bill.sequence')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('progressive.project.claim.sequence')
        return super(ProgressiveClaim, self).create(vals)

    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: _('New'), ondelete='cascade')
    active = fields.Boolean(string='Active', default=True)
    start_date = fields.Date(string="Start Date", tracking=True, readonly=True,
                             states={'draft': [('readonly', False)]})
    end_date = fields.Date(string="End Date", tracking=True, readonly=True,
                           states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    project_id = fields.Many2one('project.project', string="Project")
    project_director = fields.Many2one('res.users', string='Project Director')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch",
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    contract_amount = fields.Float(string='Contract Amount', compute="_compute_contract_amount")
    dp_method = fields.Selection([
        ('fix', 'Fixed'),
        ('per', 'Percentage')
    ], string="Down Payment Method", default=False)
    down_payment = fields.Float(string="Down Payment")
    dp_amount = fields.Float(string="Down Payment")
    retention1 = fields.Float(string="Retention 1")
    retention2 = fields.Float(string="Retention 2")
    retention1_amount = fields.Float(string="Retention 1 Amount", compute="_compute_total_retention1")
    retention2_amount = fields.Float(string="Retention 2 Amount", compute="_compute_total_retention2")

    tax_id = fields.Many2many('account.tax', 'taxes', string="Taxes")
    vat_tax = fields.Many2many('account.tax', 'vat_tax', string="VAT Tax")
    income_tax = fields.Many2many('account.tax', 'income_tax', string="Income Tax")
    payment_term = fields.Many2one('account.payment.term', 'Payment Term')
    analytic_idz = fields.Many2many('account.analytic.tag', string='Analytic Group',
                                    domain="[('company_id', '=', company_id)]")
    progress_full_approved = fields.Boolean(string="Progress Full Approved", compute="_onchange_progress_full_approved")
    progress_full_invoiced = fields.Boolean(string="Progress Full Invoiced", compute="_onchange_progress_full_invoiced")
    count_invoice = fields.Integer(compute="_compute_count_invoices")
    count_bill = fields.Integer(compute="_compute_count_invoices")
    progressive_bill = fields.Boolean('Progressive Bill')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=1, default='draft')

    actual_progress = fields.Float(string="Actual Progress", compute="_compute_actual_progress", digits=(2, 2))
    approved_progress = fields.Float(string='Approved Progress', compute="_compute_approved_progress_2", digits=(2, 2))
    requested_progress = fields.Float(string='Requested Progress', compute="_compute_requested_progress")
    invoiced_progress = fields.Float(string='Invoiced Progress', compute='_compute_count_invoices', digits=(2, 2))

    expected_retention1 = fields.Char(string="Expected Retention 1", compute="_compute_expected_retention")
    expected_retention2 = fields.Char(string="Expected Retention 2", compute="_compute_expected_retention")

    request = fields.Boolean(string="Request", compute="_onchange_request")
    request_2 = fields.Boolean(string="Request 2", compute="_onchange_request_2")
    claim_request = fields.Boolean(string="Claim Request", compute="_onchange_claim_request")
    show_claim_request = fields.Boolean(string="Show Claim Request", compute="_onchange_show_claim_request")
    show_journal_account = fields.Boolean(string="Show Journal", compute="_onchange_show_journal")
    claim_request_filled = fields.Boolean(string="Claim Request Filled", compute="_onchange_claim_request_filled")
    invoiceable = fields.Boolean(string="Invoiceable", compute="_onchange_invoiceable")
    invoiceable_progress = fields.Boolean(string="Invoiceable Progress", compute="_onchange_invoiceable_progress")
    invoiceable_rent1 = fields.Boolean(string="Invoiceable Retention 1", compute="_onchange_invoiceable_rent1")
    invoiceable_rent2 = fields.Boolean(string="Invoiceable Retention 2", compute="_onchange_invoiceable_rent2")
    rent1_avail = fields.Boolean(string="Retention 1 Available", compute="_onchange_rent1_avail")
    rent2_avail = fields.Boolean(string="Retention 2 Available", compute="_onchange_rent2_avail")
    rent2_invoice = fields.Boolean(string="Retention 2 Invoiced")
    dp_able = fields.Boolean(string="DP Able", compute="_onchange_dp_able")
    retention1_able = fields.Boolean(string="Retention 1 Able", compute="_onchange_retention1_able")
    retention2_able = fields.Boolean(string="Retention 2 Able", compute="_onchange_retention2_able")
    retention1_paid = fields.Boolean(string="Retention 1 Paid", compute="_onchange_retention1_able")
    retention2_paid = fields.Boolean(string="Retention 2 Paid", compute="_onchange_retention2_able")
    show_button_request = fields.Boolean(string="Show Button", compute="_onchange_show_button_request")
    clear_status = fields.Boolean(string="Status Clear", compute="_onchange_clear_status")
    progress_done_complete = fields.Boolean(string="Progress Done", compute="_onchange_progress_done")

    # tab Claim History
    claim_ids = fields.One2many('project.claim', 'claim_id', string="Claim History")

    # tab Jurnal Claim 
    # account_claim_ids = fields.One2many('account.move', 'journal_claim_id', string=" Journal Entries")
    project_account_claim_ids = fields.One2many('project.journal.entry', 'journal_claim_id', string=" Journal Entries")

    # tab Taxes
    taxes_ids = fields.One2many('taxes.claim', 'claim_id', string="Taxes", compute='_compute_taxes_amount', store=True)

    # tab Claim Request 
    claim_request_ids = fields.One2many('claim.request.line', 'claim_id', string="Claim Request")

    # project internal
    job_estimate_id = fields.Many2one('job.estimate', string="BOQ")

    # tab Contract 
    contract_parent = fields.Many2one('sale.order.const', string="Parent Contract")
    related_contract_so_ids = fields.Many2many("sale.order.const",
                                               relation="contract_rel_so_id",
                                               column1="sales_id",
                                               column2="order_id",
                                               string="")
    count_contract_so = fields.Integer(compute="_compute_count_contract_so")

    total_invoice = fields.Float(string="Total Amount Invoiced", compute='_compute_amount_invoice')
    total_claim = fields.Float(string="Total Amount Claimed", compute='_compute_amount_claim')
    remaining_amount = fields.Float(string="Remaining Amount to Claim", compute='_compute_remaining_amount')
    remaining_amount_invoiced = fields.Float(string="Remaining Amount Invoiced",
                                             compute='_compute_remaining_amount_invoice')
    total_work_order = fields.Integer(string="Job Order", compute='_comute_work_order')

    # Bill
    vendor = fields.Many2one(
        'res.partner', string='Vendor',
        change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_bill_id = fields.Many2one(
        'res.partner', string='Bill Address',
        change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    contract_parent_po = fields.Many2one('purchase.order', string="Parent Contract")
    related_contract_po_ids = fields.Many2many("purchase.order",
                                               relation="contract_po_rel_id",
                                               column1="purchase_id",
                                               column2="order_id",
                                               string="")
    count_contract_po = fields.Integer(compute="_compute_count_contract_po")
    count_claim_so = fields.Integer(compute="_compute_count_claim")
    count_claim_po = fields.Integer(compute="_compute_count_claim")

    is_set_custom_claim = fields.Boolean(string='Set Contract Custom Claim', default=False, store=True)
    claim_type = fields.Selection([
        ('monthly', 'Monthly Claim'),
        ('milestone', 'Milestone and Contract Term')
    ], string='Based On', default=False)
    is_create_automatically = fields.Boolean(string='Create Automatically', default=False)
    complete_progress = fields.Boolean(string="Complete Progress", default=False)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    show_claim_revise_button = fields.Binary(default=False, compute='_show_request_revise_buttons')
    project_contract = fields.Char(string="Project Contract", compute='_compute_name_project', store=True)
    reason_complete_progress = fields.Text('Reason of Complete Progress')

    # Actualization Subcontractor
    po_subcon_line_id = fields.Many2one('rfq.variable.line', string="Purchase Order Subcon Line")

    @api.onchange('progressive_bill','tax_id')
    def _onchange_domain_tax(self):
        for rec in self:
            if rec.progressive_bill == False:
                return {
                    'domain': {'tax_id': [('active', '=', True), ('type_tax_use', '=', 'sale')]}
                }
            else:
                return {
                    'domain': {'tax_id': [('active', '=', True), ('type_tax_use', '=', 'purchase')]}
                }

    @api.depends('progressive_bill', 'project_id', 'contract_parent', 'contract_parent_po')
    def _compute_name_project(self):
        for res in self:
            if res.progressive_bill == False:
                if res.project_id and res.contract_parent:
                    name = res.project_id.name + ' - ' + res.contract_parent.name
                else:
                    name = False
            else:
                if res.project_id and res.contract_parent_po:
                    name = res.project_id.name + ' - ' + res.contract_parent_po.name
                else:
                    name = False

            res.project_contract = name

    def _show_request_revise_buttons(self):
        for claim in self:
            director = claim.project_id.project_director
            if self.env.user.id == director.id:
                claim.show_claim_revise_button = True
            else:
                claim.show_claim_revise_button = False

    # @api.onchange('project_id')
    # def _onchange_project_id_branch(self):
    #     for rec in self:
    #         project = rec.project_id
    #         if project:
    #             rec.branch_id = project.branch_id.id
    #         else:
    #             rec.branch_id = False

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if rec.progressive_bill == False:
                return {
                    'domain': {
                        'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'),
                                       ('company_id', '=', rec.company_id.id),
                                       ('id', 'in', rec.env.user.project_ids.ids)]}
                }
            else:
                return {
                    'domain': {
                        'project_id': [('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),
                                       ('id', 'in', rec.env.user.project_ids.ids)]}
                }

    def action_complete_progress(self):
        if self.approved_progress < self.actual_progress:
            raise ValidationError(_("Please, complete the current actual progress until invoiced first"))
        elif self.invoiced_progress < self.approved_progress:
            raise ValidationError(_("Please, complete the current approved progress until invoiced first"))
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'res_model': 'complete.progress.confirmation',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                "context": {'default_progressive_claim_id': self.id}
            }

    @api.depends('claim_ids', 'claim_ids.amount_invoice')
    def _compute_amount_invoice(self):
        total = 0
        for rec in self:
            if rec.claim_ids:
                total = sum(rec.claim_ids.mapped('amount_invoice'))
                rec.total_invoice = total
            else:
                rec.total_invoice = 0

    @api.depends('claim_ids', 'claim_ids.amount_claim')
    def _compute_amount_claim(self):
        total = 0
        for rec in self:
            if rec.claim_ids:
                total = sum(rec.claim_ids.mapped('amount_claim'))
                rec.total_claim = total
            else:
                rec.total_claim = 0

    @api.depends('claim_ids', 'total_invoice', 'total_claim')
    def _compute_remaining_amount(self):
        total = 0
        for rec in self:
            if rec.claim_ids:
                total = rec.total_invoice - rec.total_claim
                rec.remaining_amount = total
            else:
                rec.remaining_amount = 0

    @api.depends('claim_ids', 'contract_amount', 'total_invoice')
    def _compute_remaining_amount_invoice(self):
        total = 0
        for rec in self:
            if rec.claim_ids:
                total = rec.contract_amount - rec.total_invoice
                rec.remaining_amount_invoiced = total
            else:
                rec.remaining_amount_invoiced = 0

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    def _monthly_reminder_create_invoice(self):
        current_date = datetime.now()
        data = self.env['progressive.claim'].search([
            ('claim_type', '=', 'monthly'),
            ('is_create_automatically', '=', False),
            ('state', '=', 'in_progress')])
        unconditional_data = []
        unconditional_data_ids = []
        conditional_data = []
        for d in data:
            if d.dp_able == True or (
                    d.progress_full_invoiced == True and (d.invoiceable_rent1 == True or d.invoiceable_rent2 == True)):
                unconditional_data.append(d)
                unconditional_data_ids.append(d.id)
        for d in data:
            if d.progress_full_invoiced == False and d.id not in unconditional_data_ids:
                conditional_data.append(d)

        def _send_monthly_create_invoice_reminder(res):
            template_id = self.env.ref(
                'equip3_construction_accounting_operation.email_template_reminder_monthly_create_invoice')
            if res.progressive_bill == False:
                action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
            else:
                action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

            for user in res.project_id.notification_claim:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(res.id) + '&action=' + str(
                    action_id.id) + '&view_type=form&model=progressive.claim'
                ctx = {
                    'email_from': self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                    'email_to': user.partner_id.email,
                    'approver_name': user.partner_id.name,
                    'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                    'url': url,
                }
                if res.dp_able:
                    ctx['invoice_for'] = "Down Payment"
                elif res.progress_full_invoiced == True and (
                        res.invoiceable_rent1 == True or res.invoiceable_rent2 == True):
                    if res.invoiceable_rent1:
                        ctx['invoice_for'] = "Retention 1"
                    else:
                        ctx['invoice_for'] = "Retention 2"
                else:
                    ctx['invoice_for'] = "Progress"
                template_id.sudo().with_context(ctx).send_mail(res.id, True)

        def _send_create_claim_request_reminder(res):
            template_id = self.env.ref(
                'equip3_construction_accounting_operation.email_template_reminder_monthly_create_claim_request')
            if res.progressive_bill == False:
                action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
            else:
                action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

            for user in res.project_id.notification_claim:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(res.id) + '&action=' + str(
                    action_id.id) + '&view_type=form&model=progressive.claim'
                ctx = {
                    'email_from': self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                    'email_to': user.partner_id.email,
                    'approver_name': user.partner_id.name,
                    'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                    'url': url,
                }
                template_id.sudo().with_context(ctx).send_mail(res.id, True)

        def _send_no_progress_notification(res):
            template_id = self.env.ref(
                'equip3_construction_accounting_operation.email_template_reminder_monthly_with_no_progress')
            if res.progressive_bill == False:
                action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
            else:
                action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

            for user in res.project_id.notification_claim:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(res.id) + '&action=' + str(
                    action_id.id) + '&view_type=form&model=progressive.claim'
                ctx = {
                    'email_from': self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                    'email_to': user.partner_id.email,
                    'approver_name': user.partner_id.name,
                    'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                    'url': url,
                }
                template_id.sudo().with_context(ctx).send_mail(res.id, True)

        month_dict = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        week_add_dict = {
            "first": 0, "second": 7, "third": 14, "last": 21
        }
        weekday_dict = {
            "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
        }
        for rec in unconditional_data:
            if rec.start_year:
                if rec.repeat_on_month == "date":
                    year = int(rec.start_year.name)
                    month = month_dict[rec.start_month]
                    date = int(rec.repeat_day)
                    minute = 1  # change as needed

                    scheduled_claim_date = datetime(year, month, date, 0, minute) - timedelta(hours=7)

                    # print("Scheduled Invoice create time: ", scheduled_claim_date)
                    # print("Current time: ", current_date)

                    while True:
                        if scheduled_claim_date == current_date:
                            _send_monthly_create_invoice_reminder(rec)
                            break
                        elif scheduled_claim_date < current_date:
                            if (current_date - scheduled_claim_date) <= timedelta(seconds=30):
                                _send_monthly_create_invoice_reminder(rec)
                                break
                            else:
                                if month < 12:
                                    month += 1
                                else:
                                    month = 1
                                    year += 1
                                scheduled_claim_date = datetime(year, month, date, 0, minute) - timedelta(hours=7)
                        else:
                            if (scheduled_claim_date - current_date) <= timedelta(seconds=30):
                                _send_monthly_create_invoice_reminder(rec)
                            break
                elif rec.repeat_on_month == "day":
                    year = int(rec.start_year.name)
                    month = month_dict[rec.start_month]
                    dates = [d for d in Calendar(6).itermonthdates(year, month)]
                    date_num = week_add_dict[rec.repeat_week] + weekday_dict[rec.repeat_weekday]
                    scheduled_claim_date = datetime(dates[date_num].year, dates[date_num].month, dates[date_num].day, 0,
                                                    1) - timedelta(hours=7)

                    while True:
                        if scheduled_claim_date == current_date:
                            _send_monthly_create_invoice_reminder(rec)
                            break
                        elif scheduled_claim_date < current_date:
                            if (current_date - scheduled_claim_date) <= timedelta(seconds=30):
                                _send_monthly_create_invoice_reminder(rec)
                                break
                            if month < 12:
                                month += 1
                            else:
                                month = 1
                                year += 1
                            dates = [d for d in Calendar(6).itermonthdates(year, month)]
                            scheduled_claim_date = datetime(dates[date_num].year, dates[date_num].month,
                                                            dates[date_num].day, 0, 1) - timedelta(
                                hours=7)  # 18:00 GMT+0
                        else:
                            if (scheduled_claim_date - current_date) <= timedelta(seconds=30):
                                _send_monthly_create_invoice_reminder(rec)
                            break
        for rec in conditional_data:
            if rec.start_year:
                if rec.repeat_on_month == "date":
                    year = int(rec.start_year.name)
                    month = month_dict[rec.start_month]
                    date = int(rec.repeat_day)
                    minute = 1  # change as needed

                    scheduled_claim_date = datetime(year, month, date, 0, minute) - timedelta(hours=7)

                    # print("CONDITIONAL DATA")
                    # print("Scheduled Invoice create time: ", scheduled_claim_date)
                    # print("Current time: ", current_date)

                    while True:
                        if scheduled_claim_date == current_date:
                            if rec.invoiced_progress < rec.approved_progress:
                                _send_monthly_create_invoice_reminder(rec)
                            else:
                                if rec.approved_progress < rec.actual_progress:
                                    _send_create_claim_request_reminder(rec)
                                else:
                                    _send_no_progress_notification(rec)
                            break
                        elif scheduled_claim_date < current_date:
                            if (current_date - scheduled_claim_date) <= timedelta(seconds=30):
                                if rec.invoiced_progress < rec.approved_progress:
                                    _send_monthly_create_invoice_reminder(rec)
                                else:
                                    if rec.approved_progress < rec.actual_progress:
                                        _send_create_claim_request_reminder(rec)
                                    else:
                                        _send_no_progress_notification(rec)
                                break
                            else:
                                if month < 12:
                                    month += 1
                                else:
                                    month = 1
                                    year += 1
                                scheduled_claim_date = datetime(year, month, date, 0, minute) - timedelta(hours=7)
                        else:
                            if (scheduled_claim_date - current_date) <= timedelta(seconds=30):
                                if rec.invoiced_progress < rec.approved_progress:
                                    _send_monthly_create_invoice_reminder(rec)
                                else:
                                    if rec.approved_progress < rec.actual_progress:
                                        _send_create_claim_request_reminder(rec)
                                    else:
                                        _send_no_progress_notification(rec)
                            break
                elif rec.repeat_on_month == "day":
                    year = int(rec.start_year.name)
                    month = month_dict[rec.start_month]
                    dates = [d for d in Calendar(6).itermonthdates(year, month)]
                    date_num = week_add_dict[rec.repeat_week] + weekday_dict[rec.repeat_weekday]
                    scheduled_claim_date = datetime(dates[date_num].year, dates[date_num].month, dates[date_num].day, 0,
                                                    1) - timedelta(hours=7)

                    while True:
                        if scheduled_claim_date == current_date:
                            if rec.invoiced_progress < rec.approved_progress:
                                _send_monthly_create_invoice_reminder(rec)
                            else:
                                if rec.approved_progress < rec.actual_progress:
                                    _send_create_claim_request_reminder(rec)
                                else:
                                    _send_no_progress_notification(rec)
                            break
                        elif scheduled_claim_date < current_date:
                            if (current_date - scheduled_claim_date) <= timedelta(seconds=30):
                                if rec.invoiced_progress < rec.approved_progress:
                                    _send_monthly_create_invoice_reminder(rec)
                                else:
                                    if rec.approved_progress < rec.actual_progress:
                                        _send_create_claim_request_reminder(rec)
                                    else:
                                        _send_no_progress_notification(rec)
                                break
                            if month < 12:
                                month += 1
                            else:
                                month = 1
                                year += 1
                            dates = [d for d in Calendar(6).itermonthdates(year, month)]
                            scheduled_claim_date = datetime(dates[date_num].year, dates[date_num].month,
                                                            dates[date_num].day, 0, 1) - timedelta(
                                hours=7)  # 18:00 GMT+0
                        else:
                            if (scheduled_claim_date - current_date) <= timedelta(seconds=30):
                                if rec.invoiced_progress < rec.approved_progress:
                                    _send_monthly_create_invoice_reminder(rec)
                                else:
                                    if rec.approved_progress < rec.actual_progress:
                                        _send_create_claim_request_reminder(rec)
                                    else:
                                        _send_no_progress_notification(rec)
                            break

    def _automatic_create_invoice(self):
        data = self.env['progressive.claim'].search([])
        for rec in data:
            def _update_request(res):
                if res.dp_able == False and res.claim_request == True and res.clear_status == True and res.state == "in_progress":
                    context = {'request_for': 'progress',
                               'progressive_bill': res.progressive_bill,
                               'project_id': res.project_id.id or False,
                               'partner_id': res.partner_id.id or False,
                               'vendor': res.vendor.id or False,
                               'branch_id': res.branch_id.id or False,
                               'project_director': res.project_director.id or False,
                               'contract_amount': res.contract_amount,
                               'down_payment': res.down_payment,
                               'dp_amount': res.dp_amount,
                               'retention1': res.retention1,
                               'retention2': res.retention2,
                               'retention1_amount': res.retention1_amount,
                               'retention2_amount': res.retention2_amount,
                               'progressive_claim_id': res.id,
                               'contract_parent': res.contract_parent.id or False,
                               'contract_parent_po': res.contract_parent_po.id or False,
                               'state': 'to_approve',
                               }

                    claim_request_id = self.env['claim.request'].create(context)
                    request_line = []
                    domain = [('project_id', '=', res.project_id.id), ('sale_order', '=', res.contract_parent.id),
                              ('state', '!=', 'draft'), ('claim_request', '=', True),
                              ('is_greater_current_progress', '=', True)]
                    if domain:
                        had_claim_request = self.env['claim.request.line'].search(
                            [('state', '!=', 'to_approve')]).mapped('request_id')
                        domain_2 = [('request_id', 'in', had_claim_request.ids), ('project_id', '=', res.project_id.id)]
                        project_task_ids = self.env['const.request.line'].search(domain_2).mapped('work_order')
                        ids = []
                        for task in project_task_ids:
                            if task.progress_task <= task.last_progress:
                                ids.append(task.id)
                        domain += [('id', 'not in', ids)]
                    work_orders = self.env['project.task'].search(domain)
                    progress = 0
                    for w in work_orders:
                        line = self.env['const.request.line'].create({
                            'work_order': w.id,
                            'stage_new': w.stage_new and w.stage_new.id or False,
                            'assigned_to': w.assigned_to and w.assigned_to.id or False,
                            'completion_date': w.actual_end_date,
                            'stage_weightage': w.stage_weightage,
                            'work_progress': w.progress_task,
                            'work_weightage': w.work_weightage,
                            'last_progress': w.last_progress,
                            'wo_prog_temp': w.wo_prog_temp,
                            'request_id': claim_request_id.id,
                        })
                        progress += line.progress
                        request_line.append(line.id)
                    claim_request_id.write({
                        'request_line_ids': [(6, 0, request_line)],
                        'requested_progress': progress
                    })
                    claim_request_id.send_request()
                    claim_request_line = self.env['claim.request.line'].search(
                        [('claim_id', '=', res.id), ('request_id', '=', claim_request_id.id)])
                    if claim_request_line:
                        if claim_request_id.is_claim_request_approval_matrix:
                            claim_request_line.action_confirm_approving_matrix(is_from_monthly=True)

            def _update_invoice(res):
                if res.state == "in_progress":
                    context = {}
                    if res.invoiceable_progress == True:
                        const = self.env['project.claim'].search(
                            [('claim_id', '=', res.id), ('claim_for', '=', 'progress'),
                             ('progressline', '=', res.invoiced_progress)], limit=1)
                        tot = sum(const.mapped('gross_amount'))
                        context = {'invoice_for': 'progress',
                                   'progressive_bill': res.progressive_bill,
                                   'approved_progress': res.approved_progress,
                                   'invoice_progress': res.approved_progress,
                                   'contract_amount': res.contract_amount,
                                   'last_progress': res.invoiced_progress,
                                   'down_payment': res.down_payment,
                                   'last_amount': tot,
                                   'dp_amount': res.dp_amount,
                                   'retention1': res.retention1,
                                   'retention2': res.retention2,
                                   'retention1_amount': res.retention1_amount,
                                   'retention2_amount': res.retention2_amount,
                                   'tax_id': [(6, 0, [v.id for v in res.tax_id])],
                                   'progressive_claim_id': res.id,
                                   'method': 'per'
                                   }

                    if context:
                        # print("Invoice Value: ", context)

                        def _get_history_lines_vals(inv_ids):
                            vals = []
                            if len(inv_ids) > 0:
                                for inv in inv_ids:
                                    val = {
                                        'invoice_id': inv.id
                                    }
                                    vals.append((0, 0, val))
                            if len(vals) > 0:
                                rec.claim_ids = False
                            return vals

                        wizard_invoice = self.env['progressive.invoice.wiz'].create(context)
                        wizard_invoice.create_invoice()
                        inv_ids = self.env['account.move'].search([('claim_id', '=', res.id)], order='create_date')
                        get_history_lines = _get_history_lines_vals(inv_ids)

                        if len(get_history_lines) > 0:
                            history_lines = get_history_lines
                        res.claim_ids = history_lines
                        inv_id = self.env['account.move'].search([('claim_id', '=', res.id)], order='create_date desc',
                                                                 limit=1)
                        if inv_id:
                            template_id = self.env.ref(
                                'equip3_construction_accounting_operation.email_template_reminder_invoice_created')
                            if inv_id.move_type == "in_invoice":
                                action_id = self.env.ref('account.action_move_in_invoice_type')
                            else:
                                action_id = self.env.ref('account.action_move_out_invoice_type')
                            for user in res.project_id.notification_claim:
                                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                                url = base_url + '/web#id=' + str(inv_id.id) + '&action=' + str(
                                    action_id.id) + '&view_type=form&model=account.move'
                                ctx = {
                                    'email_from': self.env['res.partner'].search(
                                        [('name', '=', 'System Notification')]).email,
                                    'email_to': user.partner_id.email,
                                    'approver_name': user.partner_id.name,
                                    'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                                    'url': url,
                                }
                                if context['invoice_for'] == 'down_payment':
                                    ctx['invoice_for'] = 'down payment'
                                elif context['invoice_for'] == 'progress':
                                    ctx['invoice_for'] = 'progress'
                                elif context['invoice_for'] == 'retention1':
                                    ctx['invoice_for'] = 'retention 1'
                                else:
                                    ctx['invoice_for'] = 'retention 2'

                                if inv_id.move_type == "in_invoice":
                                    ctx['type'] = 'bill'
                                else:
                                    ctx['type'] = 'invoice'
                                template_id.sudo().with_context(ctx).send_mail(res.id, True)

            # debugging
            # print("=========================================")
            # print("dp_able: ", rec.dp_able)
            # print("invoiceable_progress", rec.invoiceable_progress)
            # print("claim_request", rec.claim_request)
            # print("clear_status", rec.clear_status)
            # print("progress_full_invoiced", rec.progress_full_invoiced)
            # print("State: ", rec.state)
            # print(rec.taxes_ids)
            # print(rec.tax_id)
            # print(rec.claim_ids)

            if rec.claim_type == "monthly" and rec.is_create_automatically:
                if rec.state == "draft":
                    rec.claim_confirm()

                if rec.repeat_on_month == "date":
                    date = int(rec.repeat_day)
                    hour = 0
                    minute = 0  # change as needed
                    year = (datetime.now() + timedelta(hours=7)).year
                    month = (datetime.now() + timedelta(hours=7)).month

                    claim_request_date = datetime(year, month, date, hour, minute)
                    claim_date = datetime(year, month, date, hour, minute)
                    current_date = datetime.now()
                    # print("Invoice create time: ", claim_date)
                    # print("Current time: ", current_date)
                    # print("Claim request time: ", claim_request_date)

                    if claim_request_date.date() == current_date.date():
                        _update_request(rec)
                        _update_invoice(rec)

                    # while True:
                    #     if claim_request_date == current_date:
                    #         _update_request(rec)
                    #         break
                    #     elif claim_request_date < current_date:
                    #         if (current_date - claim_request_date) <= timedelta(seconds=30):
                    #             _update_request(rec)
                    #             break
                    #         else:
                    #             if month < 12:
                    #                 month += 1
                    #             else:
                    #                 month = 1
                    #                 year += 1
                    #             claim_request_date = datetime(year, month, date, hour, minute) - timedelta(hours=8)
                    #     else:
                    #         if (claim_request_date - current_date) <= timedelta(seconds=30):
                    #             _update_request(rec)
                    #         break
                    #
                    # while True:
                    #     if claim_date == current_date:
                    #         _update_invoice(rec)
                    #         break
                    #     elif claim_date < current_date:
                    #         if (current_date - claim_date) <= timedelta(seconds=30):
                    #             _update_invoice(rec)
                    #             break
                    #         else:
                    #             if month < 12:
                    #                 month += 1
                    #             else:
                    #                 month = 1
                    #                 year += 1
                    #             claim_date = datetime(year, month, date, hour, minute) - timedelta(hours=7)
                    #     else:
                    #         if (claim_date - current_date) <= timedelta(seconds=30):
                    #             _update_invoice(rec)
                    #         break
                elif rec.repeat_on_month == "day":
                    week_add_dict = {
                        "first": 0, "second": 7, "third": 14, "last": 21
                    }
                    weekday_dict = {
                        "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
                    }
                    year = (datetime.now() + timedelta(hours=7)).year
                    month = (datetime.now() + timedelta(hours=7)).month
                    hour = int(rec.repeat_time)
                    dates = [d for d in Calendar(6).itermonthdates(year, month)]
                    date_num = week_add_dict[rec.repeat_week] + weekday_dict[rec.repeat_weekday]
                    claim_request_date = datetime(dates[date_num].year, dates[date_num].month, dates[date_num].day,
                                                  hour) - timedelta(hours=8)
                    claim_date = datetime(dates[date_num].year, dates[date_num].month, dates[date_num].day,
                                          hour) - timedelta(hours=7)
                    current_date = datetime.now()

                    while True:
                        # _update_request(rec)
                        # _update_invoice(rec)
                        if claim_request_date == current_date:
                            _update_request(rec)
                            break
                        elif claim_request_date < current_date:
                            if (current_date - claim_request_date) <= timedelta(seconds=30):
                                _update_request(rec)
                                break
                            if month < 12:
                                month += 1
                            else:
                                month = 1
                                year += 1
                            dates = [d for d in Calendar(6).itermonthdates(year, month)]
                            claim_request_date = datetime(dates[date_num].year, dates[date_num].month,
                                                          dates[date_num].day, hour) - timedelta(hours=8)  # 17:00 GMT+0
                        else:
                            if (claim_request_date - current_date) <= timedelta(seconds=30):
                                _update_request(rec)
                            break

                    while True:
                        if claim_date == current_date:
                            _update_invoice(rec)
                            break
                        elif claim_date < current_date:
                            if (current_date - claim_date) <= timedelta(seconds=30):
                                _update_invoice(rec)
                                break
                            if month < 12:
                                month += 1
                            else:
                                month = 1
                                year += 1
                            dates = [d for d in Calendar(6).itermonthdates(year, month)]
                            claim_date = datetime(dates[date_num].year, dates[date_num].month, dates[date_num].day,
                                                  hour)  # 18:00 GMT+0
                        else:
                            if (claim_date - current_date) <= timedelta(seconds=30):
                                _update_invoice(rec)
                            break

    # tab taxes
    @api.depends('claim_ids.amount_untaxed', 'claim_ids.invoice_status')
    def _compute_taxes_amount(self):
        for rec in self:
            if rec.tax_id:
                for tax_line in rec.taxes_ids:
                    claim_amount_tax = 0
                    for cl in rec.claim_ids:
                        if cl.invoice_status not in ['rejected', 'canceled'] \
                                and tax_line.tax_id.id in cl.invoice_id.tax_id.ids:
                            claim_amount_tax += cl.amount_untaxed * tax_line.tax_id.amount / 100
                    tax_line.amount_tax = claim_amount_tax

    @api.depends('claim_ids')
    def _onchange_dp_able(self):
        for res in self:
            cont = self.env['project.claim'].search([('claim_id', '=', res.id), ('claim_for', '=', 'down_payment')])
            claim_dp_100 = False

            for claim in cont:
                if claim.claim_name.__contains__('100.0%'):
                    claim_dp_100 = True
                    break

            if res.down_payment > 0:
                if claim_dp_100 == True:
                    res.dp_able = False
                else:
                    res.dp_able = True
            else:
                res.dp_able = False

    @api.depends('claim_request_ids')
    def _onchange_show_claim_request(self):
        for res in self:
            if not res.claim_request_ids:
                res.show_claim_request = False
            else:
                res.show_claim_request = True

    @api.depends('project_account_claim_ids')
    def _onchange_show_journal(self):
        for res in self:
            if not res.project_account_claim_ids:
                res.show_journal_account = False
            else:
                res.show_journal_account = True

    def _onchange_claim_request_filled(self):
        for res in self:
            claim_progress = res.env['claim.request.line'].search(
                [('claim_id', '=', res.id), ('request_for', '=', 'progress')])
            claim_tot = sum(claim_progress.mapped('approved_progress'))
            if claim_tot == 100:
                res.claim_request_filled = True
            else:
                res.claim_request_filled = False

    @api.depends('actual_progress', 'approved_progress')
    def _onchange_request(self):
        for res in self:
            if res.actual_progress > res.approved_progress:
                res.request = True
            else:
                res.request = False

    @api.depends('actual_progress', 'requested_progress')
    def _onchange_request_2(self):
        for res in self:
            if res.actual_progress > res.requested_progress:
                res.request_2 = True
            else:
                res.request_2 = False

    def _onchange_clear_status(self):
        for res in self:
            status = self.env['claim.request.line'].search([('claim_id', '=', res.id), ('state', '=', 'to_approve')])
            if len(status) > 0:
                res.clear_status = False
            else:
                res.clear_status = True

    @api.depends('request', 'request_2', 'claim_request_filled')
    def _onchange_claim_request(self):
        for res in self:
            if res.request == True and res.request_2 == True and res.claim_request_filled == False and res.clear_status == True:
                res.claim_request = True
            else:
                res.claim_request = False

    @api.depends('dp_able', 'claim_request', 'clear_status')
    def _onchange_show_button_request(self):
        for res in self:
            if res.dp_able == False and res.claim_request == True and res.clear_status == True:
                res.show_button_request = True
            else:
                res.show_button_request = False

    @api.depends('approved_progress', 'invoiced_progress')
    def _onchange_invoiceable(self):
        for res in self:
            if res.approved_progress > res.invoiced_progress:
                res.invoiceable = True
            elif res.approved_progress == res.invoiced_progress:
                res.invoiceable = False
            else:
                res.invoiceable = False

    @api.depends('dp_able', 'invoiceable', 'complete_progress')
    def _onchange_invoiceable_progress(self):
        for res in self:
            if (res.dp_able == False and res.invoiceable == True and res.complete_progress != True):
                res.invoiceable_progress = True
            else:
                res.invoiceable_progress = False

    def _onchange_retention1_able(self):
        for res in self:
            rent1 = self.env['project.claim'].search([('claim_id', '=', res.id), ('claim_for', '=', 'retention1')])
            claim_retention_100 = False

            for claim in rent1:
                if claim.claim_name.__contains__('100.0%'):
                    claim_retention_100 = True
                    break

            if res.retention1 > 0:
                if claim_retention_100 == True:
                    res.retention1_able = False
                    res.retention1_paid = True
                else:
                    res.retention1_able = True
                    res.retention1_paid = False
            else:
                res.retention1_able = False
                res.retention1_paid = False

    @api.depends('retention1')
    def _onchange_rent1_avail(self):
        for res in self:
            if res.retention1 > 0:
                res.rent1_avail = True
            elif res.retention1 == 0:
                res.rent1_avail = False
            else:
                res.rent1_avail = False

    @api.depends('progress_full_invoiced', 'complete_progress', 'retention1_able', 'rent1_avail')
    def _onchange_invoiceable_rent1(self):
        for res in self:
            if ((
                    res.progress_full_invoiced == True or res.complete_progress == True) and res.retention1_able == True and res.rent1_avail == True):
                res.invoiceable_rent1 = True
            else:
                res.invoiceable_rent1 = False

    @api.depends('progress_full_invoiced', 'complete_progress')
    def _onchange_progress_done(self):
        for res in self:
            if res.progress_full_invoiced == True or res.complete_progress == True:
                res.progress_done_complete = True
            else:
                res.progress_done_complete = False

    def _onchange_retention2_able(self):
        for res in self:
            rent2 = self.env['project.claim'].search([('claim_id', '=', res.id), ('claim_for', '=', 'retention2')])

            claim_retention_100 = False

            for claim in rent2:
                if claim.claim_name.__contains__('100.0%'):
                    claim_retention_100 = True
                    break

            if res.retention2 > 0:
                if claim_retention_100 == True:
                    res.retention2_able = False
                    res.retention2_paid = True
                else:
                    res.retention2_able = True
                    res.retention2_paid = False
            else:
                res.retention2_able = False
                res.retention2_paid = False

    # def _onchange_retention2_able(self):
    #     for res in self:
    #         rent2 = self.env['project.claim'].search([('claim_id', '=', res.id), ('claim_for', '=', 'retention2'), ('progress', '=', 100)],limit=1)
    #         if len(rent2) > 0:
    #             res.retention2_able = False
    #         else:
    #             res.retention2_able = True

    @api.depends('retention2')
    def _onchange_rent2_avail(self):
        for res in self:
            if res.retention2 > 0:
                res.rent2_avail = True
            elif res.retention2 == 0:
                res.rent2_avail = False
            else:
                res.rent2_avail = False

    @api.depends('progress_full_invoiced', 'complete_progress', 'retention1_able', 'rent2_avail', 'retention2_able')
    def _onchange_invoiceable_rent2(self):
        for res in self:
            if ((
                    res.progress_full_invoiced == True or res.complete_progress == True) and res.retention1_able == False and res.rent2_avail == True and res.retention2_able == True):
                res.invoiceable_rent2 = True
            else:
                res.invoiceable_rent2 = False

    def _comute_work_order(self):
        work_count = 0
        for work in self:
            if not work.progressive_bill:
                work_count = self.env['project.task'].search_count(
                    [('project_id', '=', work.project_id.id),('state', 'in', ('inprogress', 'pending', 'complete')),
                     ('sale_order', '=', work.contract_parent.id), ])
                work.total_work_order = work_count
            elif work.progressive_bill:
                work_count = self.env['project.task'].search_count(
                    [('project_id', '=', work.project_id.id), ('purchase_subcon', '=', work.contract_parent_po.id),
                     ('state', 'in', ('inprogress', 'pending', 'complete')), ('is_subcon', '=', True)])
                work.total_work_order = work_count
        return work_count

    def action_work_order(self):
        tree_view = self.env.ref('equip3_construction_masterdata.view_task_tree_project').id
        return {
            'name': ("Job Orders"),
            'views': [(tree_view, "tree"), (False, "form")],
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'context': {'default_project_id': self.project_id.id,
                        'default_sale_order': self.contract_parent.id},
            'target': 'current',
            'domain': [('project_id', '=', self.project_id.id), ('state', 'in', ('inprogress', 'pending', 'complete')),
                       ('sale_order', '=', self.contract_parent.id)],
        }

    def action_work_order_sub(self):
        tree_view = self.env.ref('equip3_construction_masterdata.view_task_tree_project').id
        return {
            'name': ("Job Orders Subcon"),
            'views': [(tree_view, "tree"), (False, "form")],
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'context': {'default_project_id': self.project_id.id,
                        'default_purchase_subcon': self.contract_parent_po.id,
                        'default_is_subcon': True},
            'target': 'current',
            'domain': [('project_id', '=', self.project_id.id), ('purchase_subcon', '=', self.contract_parent_po.id),
                       ('state', 'in', ('inprogress', 'pending', 'complete')), ('is_subcon', '=', True)],
        }

    @api.depends('approved_progress')
    def _onchange_progress_full_approved(self):
        for res in self:
            if res.approved_progress == 100:
                res.progress_full_approved = True
            else:
                res.progress_full_approved = False

    @api.depends('invoiced_progress')
    def _onchange_progress_full_invoiced(self):
        for res in self:
            if res.invoiced_progress == 100:
                res.progress_full_invoiced = True
            else:
                res.progress_full_invoiced = False

    # @api.depends('claim_request_ids')
    def _compute_approved_progress_2(self):
        total = 0
        for rec in self:
            filtered_claim_request_lines = rec.claim_request_ids.filtered(lambda x: x.request_for == 'progress')
            total = sum(filtered_claim_request_lines.mapped('approved_progress'))
            rec.approved_progress = total
        return total
        # total = 0
        # for res in self:
        # claim_progress = self.env['claim.request.line'].search([('claim_id', '=', res.id), ('request_for', '=', 'progress')])
        # total = sum(claim_progress.mapped('approved_progress'))
        # filtered_claim_request_lines = res.claim_request_ids.filtered(lambda x: x.request_for == 'progress')
        # res.approved_progress = sum(filtered_claim_request_lines.mapped('approved_progress'))
        # return total

    # @api.depends('claim_request_ids')
    def _compute_requested_progress(self):
        total = 0
        for rec in self:
            filtered_claim_request_lines = rec.claim_request_ids.filtered(lambda x: x.request_for == 'progress')
            total = sum(filtered_claim_request_lines.mapped('requested_progress_2'))
            rec.requested_progress = total
        return total
        # total_1 = 0
        # for res in self:
        #     claim_progress = self.env['claim.request.line'].search([('claim_id', '=', res.id), ('request_for', '=', 'progress')])
        #     total_1 = sum(claim_progress.mapped('requested_progress_2'))
        #     res.requested_progress = total_1
        # return total_1

    # @api.depends('progressive_bill')
    def _compute_actual_progress(self):
        total = 0
        for work in self:
            if work.progressive_bill == False:
                work_order = self.env['project.task'].search(
                    [('project_id', '=', work.project_id.id), ('sale_order', '=', work.contract_parent.id),
                     ('state', 'in', ('inprogress', 'pending', 'complete'))])
                total = sum(work_order.mapped('contract_completion'))
                work.actual_progress = total
            elif work.progressive_bill == True:
                work_order = self.env['project.task'].search(
                    [('project_id', '=', work.project_id.id), ('purchase_subcon', 'in', work.related_contract_po_ids.ids),
                     ('state', 'in', ('inprogress', 'pending', 'complete')), ('is_subcon', '=', True)])
                total = sum(work_order.mapped('contract_completion_subcon'))
                work.actual_progress = total
        return total


class ProjectClaim(models.Model):
    _name = 'project.claim'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _rec_name = 'claim_name'
    _order = 'sequence'
    _description = "Project Claim"

    @api.depends('claim_id.claim_ids', 'claim_id.claim_ids.sequence')
    def _sequence_ref(self):
        no = 0
        for line in self:
            no += 1
            line.sr_no = no

    claim_id = fields.Many2one('progressive.claim', string="Claim", ondelete='cascade')
    active = fields.Boolean(related='claim_id.active', string='Active')
    project_id = fields.Many2one(related='claim_id.project_id', string="Project")
    invoice_id = fields.Many2one('account.move', 'Invoice', ondelete='cascade')
    company_id = fields.Many2one(related='claim_id.company_id', string='Company', readonly=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id', string="Currency", readonly=True)
    claim_name = fields.Char(string="Claim ID", related='invoice_id.claim_description')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", related='invoice_id.invoice_date')
    progressline = fields.Float(string='Progress (%)', related='invoice_id.progressline', digits=(2, 2))
    gross_amount = fields.Monetary(string="Gross Amount", related='invoice_id.gross_amount',
                                   currency_field='currency_id')
    dp_deduction = fields.Monetary(string="DP Deduction", related='invoice_id.dp_deduction',
                                   currency_field='currency_id')
    retention_deduction = fields.Monetary(string="Retention Deduction", related='invoice_id.retention_deduction',
                                          currency_field='currency_id')
    amount_deduction = fields.Monetary(string="Amount After Deduction", related='invoice_id.amount_deduction',
                                       currency_field='currency_id')
    paid_invoice = fields.Monetary(string="Paid Invoice", currency_field='currency_id', compute='_compute_invoice')
    paid_bill = fields.Monetary(string="Paid Bill", currency_field='currency_id', compute='_compute_invoice')
    amount_untaxed = fields.Float(string='Amount Untaxed', related='invoice_id.amount_untaxed_2',
                                  currency_field='currency_id')
    tax_amount = fields.Monetary(string="Tax Amount", related='invoice_id.tax_amount', currency_field='currency_id')
    amount_invoice = fields.Monetary(string="Amount Invoice", related='invoice_id.amount_invoice',
                                     currency_field='currency_id')
    amount_bill = fields.Monetary(string="Amount Bill", related='invoice_id.amount_invoice',
                                  currency_field='currency_id')
    amount_claim = fields.Monetary(string="Amount Claimed", related='invoice_id.total_claim',
                                   currency_field='currency_id')
    remaining_amount = fields.Monetary(string="Remaining Amount", related='invoice_id.amount_residual',
                                       currency_field='currency_id')
    invoice_status = fields.Selection(related='invoice_id.state', string='Invoice Status')
    bill_status = fields.Selection(related='invoice_id.state', string='Bill Status')
    payment_status = fields.Selection(related='invoice_id.payment_state', string='Payment Status')
    claim_for = fields.Selection(related='invoice_id.progressive_method', string='Claim Type')
    progress = fields.Float(string='Progress (%)', compute='_compute_invoice', digits=(2, 2))
    progressive_bill = fields.Boolean(related="claim_id.progressive_bill")
    contract_parent_po = fields.Many2one(related="claim_id.contract_parent_po", string="Parent Contract")
    contract_parent = fields.Many2one(related="claim_id.contract_parent", string="Parent Contract")
    billed_amount = fields.Float(string="Billed Amount")
    purchased_amount = fields.Float(string="Purchased Amount")
    tax_id = fields.Many2many(related="claim_id.tax_id", string="Taxes")
    job_estimate_id = fields.Many2one(related="claim_id.job_estimate_id", string="BOQ")
    department_type = fields.Selection(related='claim_id.department_type', string='Type of Department')

    def _compute_invoice(self):
        for rec in self:
            def _get_amount_deduction_retention(inv_id):
                vals = {
                    'dp': 0.0,
                    'retention': 0.0,
                    'progress': 0.0,
                }
                invoice_line_ids = inv_id.invoice_line_ids
                if len(invoice_line_ids) > 0:
                    for line in invoice_line_ids:
                        vals['dp'] += line.dp_deduction
                        vals['retention'] += line.retention_deduction
                        vals['progress'] += line.progress
                return vals

            def _get_paid_inv(claim_id, progressive_method):
                value = 0.0
                domain = [('claim_id', '=', claim_id.id), ('progressive_method', '=', 'progress')]
                inv_ids = self.env['account.move'].search(domain, order='create_date')
                if progressive_method != 'progress':
                    value = 0.0
                elif len(inv_ids) > 0:
                    vals = []
                    for inv in inv_ids:
                        if inv.id == rec.invoice_id.id:
                            break
                        vals.append(inv.amount_untaxed_2)
                    if len(vals) > 0:
                        value += sum(vals)
                return value

            inv_id = rec.invoice_id
            claim_id = rec.claim_id
            total_dp_deduction = 0.0
            total_retention = 0.0
            total_progress = 0.0
            progressive_method = rec.claim_for
            total_paid_invoice = _get_paid_inv(claim_id, progressive_method)
            get_amount = _get_amount_deduction_retention(inv_id)

            if get_amount['dp'] > 0:
                total_dp_deduction += get_amount['dp']
            if get_amount['retention'] > 0:
                total_retention += get_amount['retention']
            if get_amount['progress'] > 0:
                total_progress += get_amount['progress']

            rec.paid_invoice = total_paid_invoice
            rec.paid_bill = total_paid_invoice
            rec.progress = total_progress
            rec.dp_deduction = total_dp_deduction
            rec.retention_deduction = total_retention
            # if rec.payment_status in ['paid','partial']:
            #     rec.amount_claim = rec.invoice_id.amount_total - rec.invoice_id.amount_residual
            #     rec.remaining_amount = rec.invoice_id.amount_residual
            # else:
            #     rec.amount_claim = 0.0
            #     rec.remaining_amount = rec.invoice_id.amount_total


class ClaimRequest(models.Model):
    _name = "claim.request.line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Claim Request"
    _rec_name = 'request_id'
    _order = 'create_date DESC'
    _check_company_auto = True

    def confirm_request(self):
        self.write({'state': 'approved',
                    'state2': 'approved',
                    'approved_date': datetime.now(),
                    'approved_progress': self.requested_progress})
        claim_id = self.claim_id.id
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
        action['res_id'] = claim_id

    @api.depends('claim_id.claim_request_ids', 'claim_id.claim_request_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.claim_id.claim_request_ids:
                no += 1
                l.sr_no = no

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('claim.request.sequence') or '/'
    #     res = super(ClaimRequest, self).create(vals)
    #     return res

    name = fields.Char(string='Number', copy=False, required=True, readonly=True)
    active = fields.Boolean(related='claim_id.active', string='Active')
    claim_id = fields.Many2one('progressive.claim', string='Claim ID', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="No", compute="_sequence_ref")
    request_id = fields.Many2one('claim.request', string="Request ID")
    company_id = fields.Many2one(related='claim_id.company_id', string='Company')
    branch_id = fields.Many2one(related='claim_id.branch_id', string="Branch")
    creation_date = fields.Datetime(string='Creation Date')
    approved_date = fields.Datetime(string='Approved Date')
    created_by = fields.Many2one('res.users', string='Created By')
    project_id = fields.Many2one(related='claim_id.project_id', string='Project')
    partner_id = fields.Many2one(related='claim_id.partner_id', string='Customer')
    vendor = fields.Many2one(related='claim_id.vendor', string='Vendor')
    partner_request_id = fields.Many2one('res.partner', string='Request Address')
    project_director = fields.Many2one(related='claim_id.project_director', string='Project Director')
    requested_progress = fields.Float(string='Requested Progress (%)')
    requested_progress_2 = fields.Float(string='Requested Progress (%)')
    approved_progress = fields.Float(string='Approved Progress (%)')
    requested_amount = fields.Float(string='Requested Amount')
    contract_amount = fields.Float(string='Contract Amount')
    request_ids = fields.One2many('request.from.line', 'request_line_id', string="Request ID")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Request Status", tracking=True, default='draft')
    state2 = fields.Selection(related="state", tracking=False)
    request_for = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
    ], string='Requested Type')
    show_approval_buttons = fields.Binary(default=False, compute='_show_approval_buttons')
    rejected_reason = fields.Text(string="Reason")
    rejected_date = fields.Datetime(string="Rejected Date")
    progressive_bill = fields.Boolean(related="claim_id.progressive_bill")
    contract_parent_po = fields.Many2one(related="claim_id.contract_parent_po", string="Parent Contract")
    contract_parent = fields.Many2one(related="claim_id.contract_parent", string="Parent Contract")
    contract_amount = fields.Float(string='Contract Amount')
    down_payment = fields.Float(string="Down Payment")
    dp_amount = fields.Float(string="Amount")
    retention1 = fields.Float(string="Retention 1")
    retention2 = fields.Float(string="Retention 2")
    retention1_amount = fields.Float(string="Amount")
    retention2_amount = fields.Float(string="Amount")
    amount_approved = fields.Float(string='Approved Amount')
    max_claim = fields.Float(string="Maximum Claim Amount")
    currency_id = fields.Many2one(related='claim_id.currency_id', string="Currency")
    last_progress = fields.Float(string="Last Progress")
    account_1 = fields.Float(string="Account 1")
    account_2 = fields.Float(string="Account 2")
    account_3 = fields.Float(string="Account 3")
    account_4 = fields.Float(string="Account 4")
    job_estimate_id = fields.Many2one(related="claim_id.job_estimate_id", string="BOQ")
    department_type = fields.Selection(related='claim_id.department_type', string='Type of Department')
    journal_entry = fields.Many2one('account.move', string='Journal Entry', compute='_journal_entry_compute')

    def _journal_entry_compute(self):
        for res in self:
            journal = self.env['account.move'].search([('request_id', '=', res.id)])
            if journal:
                for rec in journal:
                    res.write({'journal_entry': rec.id})
            else:
                res.write({'journal_entry': False})

    def _show_approval_buttons(self):
        for claim_request in self:
            if claim_request.project_director and self.env.user.id == claim_request.project_director.id:
                claim_request.show_approval_buttons = True
            else:
                claim_request.show_approval_buttons = False

    def line_delete(self):
        for rec in self:
            last_request = self.env['claim.request.line'].search([('claim_id', '=', rec.claim_id.id)], limit=1,
                                                                 order='create_date desc')

            if rec.id != last_request.id:
                raise ValidationError(_("You can only delete the latest claim request."))

            invoiced_progress = rec.claim_id.invoiced_progress
            request_line = rec.claim_id.claim_request_ids
            sum_request = sum(request_line.mapped('approved_progress'))

            if sum_request - rec.approved_progress < invoiced_progress:
                if rec.progressive_bill == False:
                    raise ValidationError(
                        _("You cannot delete this request because the requested progress has already been invoiced."))
                else:
                    raise ValidationError(
                        _("You cannot delete this request because the requested progress has already been billed."))

            else:
                for res in rec.request_ids:
                    res.write({'wo_prog_temp': 0})

                account_journal_entry = self.env['account.move'].search([('request_id', '=', rec.id)])
                project_journal_entry = self.env['project.journal.entry'].search([('request_id', '=', rec.id)])
                request_claim = self.env['claim.request'].search([('id', '=', rec.request_id.id)])

                if account_journal_entry:
                    account_journal_entry.unlink()
                if project_journal_entry:
                    project_journal_entry.unlink()
                if project_journal_entry:
                    request_claim.unlink()

        claim_id = self.claim_id.id
        self.unlink()
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
        action['res_id'] = claim_id
        return action

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'claim.request.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            "context": {'default_claim_id': self.claim_id and self.claim_id.id or False}
        }


class RequestLinesIds(models.Model):
    _name = 'request.from.line'
    _description = 'Request Lines'

    request_line_id = fields.Many2one('claim.request.line', string="Request ID")
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    work_order = fields.Many2one('project.task', string="Work Order",
                                 domain="[('project_id', '=', parent.project_id), ('sale_order', '=', parent.contract_parent), ('state', '!=', 'draft'), ('claim_request', '=', True)]")
    stage = fields.Many2one('project.stage', string="Stage")
    stage_new = fields.Many2one('project.stage.const', string="Stage")
    worker_assigned_to = fields.Many2one('hr.employee', string="PIC")
    assigned_to = fields.Many2one('res.users', string="PIC")
    completion_date = fields.Datetime(string="Completion Date")
    stage_weightage = fields.Float(string="Stage Weightage (%)")
    work_progress = fields.Float(string="Current WO Progress (%)")
    last_progress = fields.Float(string="Last WO Progress (%)")
    work_weightage = fields.Float(string="Work Order Weightage (%)")
    progress = fields.Float(string="Progress (%)")
    progressive_bill = fields.Boolean(related="request_line_id.progressive_bill")
    work_order_sub = fields.Many2one('project.task', string="Work Order",
                                     domain="[('project_id', '=', parent.project_id), ('purchase_subcon', '=', parent.contract_parent_po), ('state', '!=', 'draft'), ('claim_request', '=', True), ('is_subcon', '=', True)]")
    state = fields.Selection(related="request_line_id.state")
    claim_id = fields.Many2one(related="request_line_id.claim_id")
    wo_prog_temp = fields.Float(string="Temporary (%)")
    contract_parent_po = fields.Many2one(related="request_line_id.contract_parent_po", string="Parent Contract")
    task_contract_po = fields.Many2one('purchase.order', string="Subcon Contract")
    contract_parent = fields.Many2one(related="request_line_id.contract_parent", string="Parent Contract")
    job_estimate_id = fields.Many2one(related="request_line_id.job_estimate_id", string="BOQ")
    department_type = fields.Selection(related='request_line_id.department_type', string='Type of Department')
    project_id = fields.Many2one(related='request_line_id.project_id', string='Project')
    work_subcon_weightage = fields.Float(string="Job Subcon Weightage")

    @api.depends('request_line_id.request_ids', 'request_line_id.request_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.request_line_id.request_ids:
                no += 1
                l.sr_no = no


class TaxesClaim(models.Model):
    _name = 'taxes.claim'
    _description = 'Taxes'
    _order = 'sequence'

    claim_id = fields.Many2one('progressive.claim', string="Claim ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    tax_id = fields.Many2one('account.tax', string="Taxes")
    amount_tax = fields.Float(string="Amount")
    currency_id = fields.Many2one(related='claim_id.currency_id', string="Currency")

    @api.depends('claim_id.taxes_ids', 'claim_id.taxes_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.claim_id.taxes_ids:
                no += 1
                l.sr_no = no


class ProjectJournalEntry(models.Model):
    _name = 'project.journal.entry'
    _description = 'Project Journal Entry'

    name = fields.Char(string="Name", default='/')
    journal_claim_id = fields.Many2one('progressive.claim', string='Claim ID', ondelete='cascade')
    project_id = fields.Many2one('project.project', string="Project")
    contract_parent = fields.Many2one('sale.order.const', string="Parent Contract")
    contract_parent_po = fields.Many2one('purchase.order', string="Parent Contract")
    job_estimate_id = fields.Many2one('job.estimate', string="BOQ")
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    request_id = fields.Many2one('claim.request.line', string="Request ID")
    attn = fields.Char(string="Attention")
    analytic_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    journal_entries_template = fields.Many2one('account.move.template', string="Journal Entries Template")
    ref = fields.Char(string="Reference")
    period_id = fields.Many2one('sh.account.period', string="Period")
    fiscal_year = fields.Many2one('sh.fiscal.year', string="Fiscal Year")
    date = fields.Date(string="Date")
    journal_id = fields.Many2one('account.journal', string="Journal")
    currency_id = fields.Many2one('res.currency', string="Currency")
    company_id = fields.Many2one('res.company', string="Company")
    branch_id = fields.Many2one('res.branch', string="Branch")
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    progressive_bill = fields.Boolean('Progressive Bill')
    line_ids = fields.One2many('project.journal.entry.line', 'journal_entry_id', string="Journal Entry Lines")
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], string="Status", default='draft')
    journal_entry = fields.Many2one('account.move', string='Journal Entry', compute='_journal_entry_compute')

    def _journal_entry_compute(self):
        for res in self:
            journal = self.env['account.move'].search([('request_id', '=', res.request_id.id)])
            if journal:
                for rec in journal:
                    res.write({'journal_entry': rec.id})
            else:
                res.write({'journal_entry': False})

    @api.depends('journal_claim_id.project_account_claim_ids', 'journal_claim_id.project_account_claim_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.journal_claim_id.project_account_claim_ids:
                no += 1
                l.sr_no = no

    def action_post(self):
        for res in self:
            res.journal_entry.action_post()
            res.write({'state': 'posted'})


class ProjectAccountLine(models.Model):
    _name = 'project.journal.entry.line'
    _description = 'Journal Items'

    journal_entry_id = fields.Many2one('project.journal.entry', string="Journal ID", ondelete='cascade')
    account_id = fields.Many2one('account.account', string="Account")
    project_scope = fields.Many2one('project.scope.line', string="Project Scope")
    section = fields.Many2one('section.line', string="Section")
    group_of_product = fields.Many2one('group.of.product', string="Group of Product")
    name = fields.Char(string="Label")
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Tags")
    amount_currency = fields.Monetary(string="Amount in Currency", currency_field='currency_id')
    tax_ids = fields.Many2many('account.tax', string="Taxes")
    tax_tag_ids = fields.Many2many('account.account.tag', string="Tags")
    currency_id = fields.Many2one('res.currency', string="Currency")
    debit = fields.Monetary(string="Debit", currency_field='currency_id')
    credit = fields.Monetary(string="Credit", currency_field='currency_id')
    company_id = fields.Many2one('res.company', string="Company")
