import ast
from odoo import api, fields, models, _
from datetime import date, datetime

class TargetKPIInherit(models.Model):
    _inherit = 'target.kpi'

    @api.depends('main_target','target_on','target_based_on_ids')
    def _compute_current_achievement(self):
        user = []
        res = super(TargetKPIInherit, self)._compute_current_achievement()
        for rec in self:
            codes = ''
            total_cost_saving = count_purchase_order_lines = current_achievement = 0
            purchase_order_lines = False
            if rec.state == 'confirm' or rec.state == 'expired' or rec.state == 'failed' or rec.state == 'succeed':
                if rec.target_based_on_ids:
                    codes = rec.target_based_on_ids.mapped('code')
                if 'purchase_order_line' in codes:
                    purchase_order_lines = self.env['purchase.order.line'].search([
                        ('agreement_id','=',False),
                        ('purchase_line_cost_saving','>',0),
                    ])
                    purchase_order_lines = purchase_order_lines.filtered(lambda p:p.order_id and p.order_id.user_id and p.order_id.user_id.id == rec.user_id.id and p.order_id.state1 in ('purchase','done') and p.order_id.date_approve.date() >= rec.from_date and p.order_id.date_approve.date() <= rec.to_date)
                    total_cost_saving += sum(purchase_order_lines.mapped('purchase_line_cost_saving'))
                    count_purchase_order_lines += len(purchase_order_lines)
                if 'purchase_tender' in codes:
                    purchase_order_lines = self.env['purchase.order.line'].search([
                        ('agreement_id','!=',False),
                        ('cost_saving','>',0)
                    ])
                    purchase_order_lines = purchase_order_lines.filtered(lambda p:p.order_id and p.order_id.user_id and p.order_id.user_id.id == rec.user_id.id and p.order_id.state1 in ('purchase','done') and p.order_id.date_approve.date() >= rec.from_date and p.order_id.date_approve.date() <= rec.to_date)
            if rec.user_id.id not in user:
                kpi_obj = self.env['target.kpi']
                team_analysis_obj = self.env['purchase.team.analysis']
                val_amount_purchased = val_cost_saving_percentage = val_cost_saving = 0
                po_obj = self.env['purchase.order']
                kpi_amount_ids = kpi_obj.search([('user_id', '=', rec.user_id.id),('target_on', '=', 'amount')])
                kpi_qty_ids = kpi_obj.search([('user_id', '=', rec.user_id.id),('target_on', '=', 'qty')])
                kpi_succeed = kpi_obj.search([('user_id', '=', rec.user_id.id),('state', '=', 'succeed')])
                if purchase_order_lines:
                    val_amount_purchased = sum(po_obj.browse(purchase_order_lines.mapped('order_id').ids).filtered(lambda x: x.state in ['purchase', 'done']).mapped('amount_total'))
                    val_cost_saving = sum(purchase_order_lines.mapped('total_cost_saving'))
                    val_cost_saving_percentage = sum(purchase_order_lines.mapped('cost_saving_percentage'))
                team_id = team_analysis_obj.search([('user_id', '=', rec.user_id.id),('branch_id', '=', rec.branch_id.id)], limit=1)
                val_amount = 0
                val_qty = 0
                for amount in kpi_amount_ids:
                    val_amount += amount.current_achievement
                for qty in kpi_qty_ids:
                    val_qty += qty.current_achievement
                if len(kpi_amount_ids) > 0:
                    avg_val_amount = val_amount / len(kpi_amount_ids)
                else:
                    avg_val_amount = 0
                if len(kpi_qty_ids):
                    avg_val_qty = val_qty / len(kpi_qty_ids)
                else:
                    avg_val_qty = 0
                if team_id:
                    team_id.write({
                        'amount_saved_from_cost_savings': val_cost_saving,
                        'number_of_successful_cost_savings': val_qty,
                        'avg_amount_saved_from_cost_savings': avg_val_amount,
                        'avg_number_of_successful_cost_savings': avg_val_qty,
                        'kpi_target': len(kpi_succeed),
                        'amount_purchased':val_amount_purchased,
                        'cost_saving': val_cost_saving,
                        'cost_saving_percentage': val_cost_saving_percentage,
                    })
                user.append(rec.user_id.id)
        return res

class PurchaseTeamAnalysis(models.Model):
    _name = 'purchase.team.analysis'
    _description = "Purchase Team Analysis"
    
    days_to_approve = fields.Float('Days to Approve')
    purchase_order_duration_to_confirm  = fields.Float('Purchase Order Duration to Confirm')
    amount_saved_from_cost_savings = fields.Float('Amount Saved from cost savings')
    number_of_successful_cost_savings = fields.Float('Number of successful cost savings')
    avg_amount_saved_from_cost_savings = fields.Float('Average Amount Saved from cost savings')
    avg_number_of_successful_cost_savings = fields.Float('Average Number of successful cost savings')
    user_id = fields.Many2one('res.users', string="Purchase Representative")
    purchase_ids = fields.Many2many('purchase.order', string="Order")
    kpi_target = fields.Float("KPI Target")
    cost_saving_percentage = fields.Float("Cost Saving Percentage")
    amount_purchased = fields.Float("Amount Purchased")
    cost_saving = fields.Float("Cost Saving Purchased")
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    days_to_approve = fields.Float('Days to Approve', compute="_compute_data", store=True)
    purchase_order_duration_to_confirm  = fields.Float('Purchase Order Duration to Confirm')
    amount_saved_from_cost_savings = fields.Float('Amount Saved from cost savings')
    number_of_successful_cost_savings = fields.Float('Number of successful cost savings')

    @api.model
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        team_analysis_obj = self.env['purchase.team.analysis']
        team_id = team_analysis_obj.search([('user_id', '=', res.user_id.id),('branch_id', '=', res.branch_id.id)])
        if not team_id:
            team_analysis_obj.create({
                'user_id': res.user_id.id,
                'purchase_ids': [(4, res.id)],
                'branch_id': res.branch_id.id
            })
        else:
            team_id.write({
                'purchase_ids': [(4, res.id)]
            })
        return res

    @api.depends('state')
    def _compute_data(self):
        for rec in self:
            if rec.state == 'rfq_approved':
                rec.days_to_approve = (datetime.now() - rec.create_date).days or 1
            if rec.state == 'purchase':
                rec.purchase_order_duration_to_confirm = (datetime.now() - rec.create_date).days or 1
            kpi_obj = self.env['target.kpi']
            kpi_ids = kpi_obj.search([('user_id', '=', rec.user_id.id)])
            kpi_ids._compute_current_achievement()
            team_analysis_obj = self.env['purchase.team.analysis']
            team_id = team_analysis_obj.search([('user_id', '=', rec.user_id.id),('branch_id', '=', rec.branch_id.id)])
            if team_id:
                avg_days_to_approve = 0
                avg_purchase_order_duration_to_confirm = 0
                for i in team_id.purchase_ids:
                    avg_days_to_approve += i.days_to_approve
                    avg_purchase_order_duration_to_confirm += i.purchase_order_duration_to_confirm
                if len(team_id.purchase_ids.filtered(lambda r: r.days_to_approve > 0)) > 0:
                    avg_days_to_approve = avg_days_to_approve / len(team_id.purchase_ids.filtered(lambda r: r.days_to_approve > 0))
                if len(team_id.purchase_ids.filtered(lambda r: r.purchase_order_duration_to_confirm > 0)) > 0:
                    avg_purchase_order_duration_to_confirm = avg_purchase_order_duration_to_confirm / len(team_id.purchase_ids.filtered(lambda r: r.purchase_order_duration_to_confirm > 0))
                team_id.write({
                    'days_to_approve': avg_days_to_approve,
                    'purchase_order_duration_to_confirm': avg_purchase_order_duration_to_confirm
                })

    @staticmethod
    def _get_empty_widget_lines(domain):
        empty_widget_lines = [
            {'name': _('Requests for Quotation'), 'states': ('draft', 'sent'), 'count': 0, 'amount': 0.0},
            {'name': _('RFQ Under Approval'), 'states': (['waiting_for_approve']), 'count': 0, 'amount': 0.0},
            {'name': _('Purchase Order'), 'states': ('purchase', 'done'), 'count': 0, 'amount': 0.0},
            {'name': _('Cancelled PO'), 'states': (['cancel']), 'count': 0, 'amount': 0.0},
            {'name': _('Purchase Request Lines'), 'states': ('purchase_request', 'pending', 'in_progress'), 'count': 0, 'amount': 0.0, 'extra': 'purchase.request'},
            {'name': _('Purchase Tender'), 'states': ('confirm', 'pending', 'bid_submission', 'bid_selection'), 'count': 0, 'amount': 0.0, 'extra': 'purchase.agreement'}
        ]
        for empty_widget_line in empty_widget_lines:
            if not empty_widget_line.get('extra'):
                empty_widget_line['domain'] = str(domain + [('state', 'in', empty_widget_line['states'])])
            elif empty_widget_line.get('extra'):
                if empty_widget_line.get('extra') == "purchase.request":
                    purchase_request_domain = []
                    for domain_line in domain:
                        temp_domain = list(domain_line)
                        if len(domain_line) == 3 and domain_line[0] == "partner_id":
                            temp_domain = [('purchase_lines.partner_id', '=', domain_line[2])]
                            purchase_request_domain.extend(temp_domain)
                        elif len(domain_line) == 3 and domain_line[0] == "user_id":
                            temp_domain = ['|', ('assigned_to', '=', domain_line[2]), ('requested_by', '=', domain_line[2])]
                            purchase_request_domain.extend(temp_domain)
                        elif len(domain_line) == 3 and domain_line[0] == "product_id":
                            domain_line = tuple(temp_domain)
                            purchase_request_domain.append(domain_line)
                        if len(domain_line) == 3 and domain_line[0] == "date_calendar_start":
                            temp_domain[0] = 'date_required'
                            domain_line = tuple(temp_domain)
                            purchase_request_domain.append(domain_line)
                    empty_widget_line['domain'] = str(purchase_request_domain + [('request_state', '=', 'purchase_request'), ('purchase_req_state', 'in', ('pending', 'in_progress'))])
                elif empty_widget_line.get('extra') == "purchase.agreement":
                    purchase_tender_domain = []
                    for domain_line in domain:
                        temp_domain = list(domain_line)
                        if len(domain_line) == 3 and domain_line[0] == "partner_id":
                            temp_domain[0] = 'partner_ids'
                            temp_domain[1] = 'in'
                            temp_domain[2] = [domain_line[2]]
                        if len(domain_line) == 3 and domain_line[0] == "user_id":
                            temp_domain[0] = 'sh_purchase_user_id'
                        if len(domain_line) == 3 and domain_line[0] == "date_calendar_start":
                            temp_domain[0] = 'sh_order_date'
                        if len(domain_line) == 3 and domain_line[0] == "product_id":
                            temp_domain[0] = 'sh_purchase_agreement_line_ids.sh_product_id'
                        domain_line = tuple(temp_domain)
                        purchase_tender_domain.append(domain_line)
                    empty_widget_line['domain'] = str(purchase_tender_domain + [('state', 'in', ('confirm', 'bid_submission', 'bid_selection')), ('pt_state', 'in', ('pending', 'bid_submission', 'bid_selection'))])
        return empty_widget_lines

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('purchase.menu_purchase_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-purchase-purchase-dashboard'})

    def _retrieve_dashboard_data_by_users(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))

        query = """
        SELECT
        po.user_id,
        partner.name,
        po.state,
        COUNT(1) as count,
        SUM(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_order po
        JOIN res_users users ON (po.user_id = users.id)
        JOIN res_partner partner ON (users.partner_id = partner.id)
        JOIN res_company comp ON (po.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE po.company_id = %s AND po.date_calendar_start >= %s AND po.date_calendar_start <= %s AND po.dp = False
        GROUP BY po.user_id, partner.name, po.state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_users_request(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))

        query = """
        SELECT
        prl.assigned_to as user_id,
        partner.name,
        prl.request_state as state,
        prl.purchase_req_state,
        COUNT(1) as count,
        SUM(prl.estimated_cost) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_request_line prl
        JOIN res_users users ON (prl.assigned_to = users.id)
        JOIN res_partner partner ON (users.partner_id = partner.id)
        JOIN res_company comp ON (prl.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE prl.company_id = %s AND prl.date_required >= %s AND prl.date_required <= %s AND prl.request_state = 'purchase_request'
        AND prl.purchase_req_state in ('pending', 'in_progress')
        GROUP BY prl.assigned_to, partner.name, prl.request_state, prl.purchase_req_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_users_pr_requested_by(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))

        query = """
        SELECT
        prl.requested_by as user_id,
        partner.name,
        prl.request_state as state,
        prl.purchase_req_state,
        COUNT(1) as count,
        SUM(prl.estimated_cost) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_request_line prl
        JOIN res_users users ON (prl.requested_by = users.id)
        JOIN res_partner partner ON (users.partner_id = partner.id)
        JOIN res_company comp ON (prl.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE prl.company_id = %s AND prl.date_required >= %s AND prl.date_required <= %s AND prl.request_state = 'purchase_request'
        AND prl.purchase_req_state in ('pending', 'in_progress')
        GROUP BY prl.requested_by, partner.name, prl.request_state, prl.purchase_req_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_users_tender(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))

        query = """
        SELECT
        pa.sh_purchase_user_id as user_id,
        partner.name,
        pa.state as state,
        pa.pt_state,
        COUNT(1) as count,
        SUM(pa.amount_total) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_agreement pa
        JOIN res_users users ON (pa.sh_purchase_user_id = users.id)
        JOIN res_partner partner ON (users.partner_id = partner.id)
        JOIN res_company comp ON (pa.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE pa.company_id = %s AND pa.sh_order_date >= %s AND pa.sh_order_date <= %s AND pa.state in ('confirm', 'bid_submission', 'bid_selection')
        AND pa.pt_state in ('pending', 'bid_submission', 'bid_selection')
        GROUP BY pa.sh_purchase_user_id, partner.name, pa.state, pa.pt_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_partners(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        po.partner_id,
        partner.name,
        po.state,
        COUNT(1) as count,
        SUM(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_order po
        JOIN res_partner partner ON (po.partner_id = partner.id)
        JOIN res_company comp ON (po.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE po.company_id = %s AND po.date_calendar_start >= %s AND po.date_calendar_start <= %s AND po.dp = False
        GROUP BY po.partner_id, partner.name, po.state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_products(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        pol.product_id,
        product_template.name,
        pol.state,
        COUNT(1) as count,
        SUM(COALESCE(pol.price_total / NULLIF(po.currency_rate, 0), pol.price_total)) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_order_line pol
        JOIN purchase_order po ON (pol.order_id = po.id)
        JOIN product_product product ON (pol.product_id = product.id)
        JOIN product_template product_template ON (product.product_tmpl_id = product_template.id)
        JOIN res_company comp ON (po.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE po.company_id = %s AND po.date_calendar_start >= %s AND po.date_calendar_start <= %s AND po.dp = False
        GROUP BY pol.product_id, product_template.name, pol.state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_products_request(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        prl.product_id,
        product.product_display_name as name,
        prl.request_state as state,
        prl.purchase_req_state,
        COUNT(1) as count,
        SUM(prl.estimated_cost) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_request_line prl
        JOIN product_product product ON (prl.product_id = product.id)
        JOIN res_company comp ON (prl.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE prl.company_id = %s AND prl.date_required >= %s AND prl.date_required <= %s AND prl.request_state = 'purchase_request'
        AND prl.purchase_req_state in ('pending', 'in_progress')
        GROUP BY prl.product_id, product.product_display_name, prl.request_state, prl.purchase_req_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_products_tender(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        pal.sh_product_id as product_id,
        product.product_display_name as name,
        pa.state as state,
        pa.pt_state,
        COUNT(1) as count,
        SUM(pal.sh_qty * pal.sh_price_unit) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_agreement_line pal
        JOIN purchase_agreement pa ON (pal.agreement_id = pa.id)
        JOIN res_company comp ON (pa.company_id = comp.id)
        JOIN product_product product ON (pal.sh_product_id = product.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE pa.company_id = %s AND pa.sh_order_date >= %s AND pa.sh_order_date <= %s AND pa.state in ('confirm', 'bid_submission', 'bid_selection')
        AND pa.pt_state in ('pending', 'bid_submission', 'bid_selection')
        GROUP BY pal.sh_product_id, product.product_display_name, pa.state, pa.pt_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_partners_request(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        pol.partner_id as partner_id,
        partner.name,
        prl.request_state as state,
        prl.purchase_req_state,
        COUNT(1) as count,
        SUM(prl.estimated_cost) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_request_line prl
        JOIN purchase_request_purchase_order_line_rel prpol ON (prpol.purchase_request_line_id = prl.id)
        JOIN purchase_order_line pol ON (pol.id = prpol.purchase_order_line_id)
        JOIN res_partner partner ON (pol.partner_id = partner.id)
        JOIN res_company comp ON (prl.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE prl.company_id = %s AND prl.date_required >= %s AND prl.date_required <= %s AND prl.request_state = 'purchase_request'
        AND prl.purchase_req_state in ('pending', 'in_progress')
        GROUP BY pol.partner_id, partner.name, prl.request_state, prl.purchase_req_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_partners_tender(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        parp.res_partner_id as partner_id,
        partner.name,
        pt.state as state,
        pt.pt_state,
        COUNT(1) as count,
        SUM(pt.amount_total) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_agreement pt
        JOIN purchase_agreement_res_partner_rel parp ON (parp.purchase_agreement_id = pt.id)
        JOIN res_partner partner ON (parp.res_partner_id = partner.id)
        JOIN res_company comp ON (pt.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE pt.company_id = %s AND pt.sh_order_date >= %s AND pt.sh_order_date <= %s AND pt.state in ('confirm', 'bid_submission', 'bid_selection')
        AND pt.pt_state in ('pending', 'bid_submission', 'bid_selection')
        GROUP BY parp.res_partner_id, partner.name, pt.state, pt.pt_state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    @api.model
    def get_dashboard_widgets(self, year, group_by='user_id'):

        if group_by == 'partner_id':
            res_model = 'res.partner'
            res = self._retrieve_dashboard_data_by_partners(year)
            purchase_request = self._retrieve_dashboard_data_by_partners_request(year)
            purchase_tender = self._retrieve_dashboard_data_by_partners_tender(year)
            res.extend(purchase_request)
            res.extend(purchase_tender)
        elif group_by == 'product_id':
            res_model = 'product.product'
            res = self._retrieve_dashboard_data_by_products(year)
            purchase_request = self._retrieve_dashboard_data_by_products_request(year)
            purchase_tender = self._retrieve_dashboard_data_by_products_tender(year)
            res.extend(purchase_request)
            res.extend(purchase_tender)
        else:
            group_by = 'user_id'
            res_model = 'res.users'
            res = self._retrieve_dashboard_data_by_users(year)
            purchase_request = self._retrieve_dashboard_data_by_users_request(year)
            purchase_request_new_data = self._retrieve_dashboard_data_by_users_pr_requested_by(year)
            purchase_tender = self._retrieve_dashboard_data_by_users_tender(year)
            res.extend(purchase_request)
            res.extend(purchase_request_new_data)
            res.extend(purchase_tender)

        dashboard_widgets = {}
        self = self.with_context(group_by=group_by)
        for line in res:
            self._append_dashboard_widgets(dashboard_widgets, line, res_model, group_by, year)
        for key, value in dashboard_widgets.items():
            for line in value.get('lines'):
                line['amount'] = '{:,.2f}'.format(line['amount'])
        return dashboard_widgets

    # @api.constrains('state', 'po_state')
    # def set_po_qty(self):
    #     for res in self:
    #         if res.state == 'purchase' or res.po_state == 'purchase':
    #             for line in res.order_line:
    #                 line.product_id.get_po_ids()

    def _prepare_widget_lines(self, dashboard_widgets, line, res_id):
        for widget_line in dashboard_widgets[res_id]['lines']:
            if line['state'] in widget_line['states']:
                if widget_line.get('extra') and widget_line.get('extra') == "purchase.request":
                    model = "purchase.request.line"
                elif widget_line.get('extra') and widget_line.get('extra') == "purchase.agreement":
                    model = "purchase.agreement"
                else:
                    model = "purchase.order"
                count = self.env[model].search_count(ast.literal_eval(widget_line['domain']))
                widget_line['count'] = count
                amount = line.get('amount', 0)
                if amount is None:
                    amount = 0
                widget_line['amount'] += round(amount, line['decimal_places'])

class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    days_to_approve = fields.Float('Days to Approve', related='order_id.days_to_approve')
    price_average_new = fields.Float('Average Cost', readonly=True, group_operator="avg")

    def _select(self):
        res = super(PurchaseReport,self)._select()
        # return res + """, (sum(l.price_subtotal) OVER (PARTITION BY l.product_id) / NULLIF(sum(l.product_qty) OVER (PARTITION BY l.product_id), 0))::decimal(16,2) AS price_average_new"""
        return res + """, (CASE WHEN po.state = 'purchase'
                            THEN
                                (
                                sum(CASE WHEN po.state = 'purchase' THEN l.price_subtotal ELSE 0 END) OVER (PARTITION BY l.product_id) /
                                NULLIF(sum(CASE WHEN po.state = 'purchase' THEN l.product_qty ELSE 0 END) OVER (PARTITION BY l.product_id), 0)
                                )::decimal(16,2)
                            ELSE
                                0
                            END
                            ) AS price_average_new
                     """


    def _group_by(self):
        res =  super(PurchaseReport,self)._group_by()
        return res + """,l.price_subtotal, l.product_qty"""


    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super(PurchaseReport, self).fields_get(allfields=allfields, attributes=attributes)
        for key in result.keys():
            if key in ('price_average'):
                result[key]['store'] = True
        return result


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.constrains('pr_state', 'purchase_req_state')
    def set_pr_qty(self):
        for res in self:
            if res.pr_state == 'approved':
                for line in res.line_ids:
                    line.product_id.get_pr_ids()

class ProductProduct(models.Model):
    _inherit = "product.product"

    po_count = fields.Float(string="Purchase Qty")
    pr_count = fields.Float(string="Purchase Request")
    purchase_req_line_ids = fields.One2many(
        'purchase.request.line',
        'product_id',
        string="Purchase Request Line",
        readonly=True,
        copy=False,
    )

    def get_po_ids(self):
        for rec in self:
            count = 0
            total = 0
            for line in rec.purchase_order_line_ids:
                if line.order_id.state == 'purchase':
                    count += line.product_qty
                    total += line.price_subtotal
            rec.write({
                'purchase_price': rec.last_purchase_price,
                'purchase_price_totals': total,
                'po_count': count
            })

    def get_pr_ids(self):
        for rec in self:
            count = 0
            for line in rec.purchase_req_line_ids:
                if line.request_id.state == 'approved':
                    count += line.product_qty
            rec.write({
                'purchase_price': rec.last_purchase_price,
                'pr_count': count
            })