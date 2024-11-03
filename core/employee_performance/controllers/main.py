# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import get_records_pager, pager as portal_pager, CustomerPortal
import logging
_logger = logging.getLogger(__name__)

class CustomerPortal(CustomerPortal):


    # def _prepare_portal_layout_values(self):
    #     values = super(CustomerPortal, self)._prepare_portal_layout_values()
    #     user = request.env.user
    #     employees = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)])
    #     team_ids = request.env['hr.employee'].sudo().search([('parent_id', '=', employees.id)])
    #     for employee in employees:
    #         domain = [('employee_id', '=', employee.id), ('state', '!=', 'draft')]
    #         domain2 = [('employee_id', 'in', team_ids.ids), ('state', '!=', 'draft')]
    #         values['performance_count'] = request.env['employee.performance'].sudo().search_count(domain)
    #         values['teamperformance_count'] = request.env['employee.performance'].sudo().search_count(domain2)
    #         return values

    def _prepare_home_portal_values(self, counters):
        values = super(CustomerPortal, self)._prepare_home_portal_values(counters)
        user = request.env.user
        HrPerformance = request.env['employee.performance']
        employees = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        team_ids = request.env['hr.employee'].sudo().search([('parent_id', '=', employees.id)])
        domain = [('employee_id', '=', employees.id),('state','!=','draft')]
        domain2 = [('employee_id', 'in', team_ids.ids), ('state','!=','draft')]
        if 'performance_count' in counters:
            values['performance_count'] = HrPerformance.search_count(domain) if HrPerformance.check_access_rights('read', raise_exception=False) else 0
        if 'teamperformance_count' in counters:
            values['teamperformance_count'] = HrPerformance.search_count(domain2) if HrPerformance.check_access_rights('read', raise_exception=False) else 0
        return values

    @http.route(['/team/performance', '/team/performance/page/<int:page>'], type='http', auth="user", website=True)
    def team_helpdesk_performance(self, page=1, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        employees = request.env['hr.employee'].sudo().search([('user_id','=',user.id)], limit=1)
        team_ids = request.env['hr.employee'].sudo().search([('parent_id', '=', employees.id)])

        domain = [('employee_id', 'in', team_ids.ids), ('state','!=','draft')]

        # pager
        teamperformance_count = request.env['employee.performance'].search_count(domain)
        pager = portal_pager(
            url="/team/performance",
            total=teamperformance_count,
            page=page,
            step=self._items_per_page
        )

        teamperformances_ids = request.env['employee.performance'].sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_performances_history'] = teamperformances_ids.ids[:100]

        values.update({
            'performances': teamperformances_ids,
            'page_name': 'teamperformance',
            'default_url': '/team/performance',
            'pager': pager,
        })
        return request.render("employee_performance.portal_team_performances", values)


    @http.route(['/my/performance', '/my/performance/page/<int:page>'], type='http', auth="user", website=True)
    def my_helpdesk_performance(self, page=1, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        # employees = request.env['hr.employee'].sudo().search([('user_id','=',user.id)])
        # for employee in employees:
        #     domain = [('employee_id', '=', employee.id)]
        #
        #     # pager
        #     performances_count = request.env['employee.performance'].search_count(domain)
        #     pager = portal_pager(
        #         url="/my/performance",
        #         total=performances_count,
        #         page=page,
        #         step=self._items_per_page
        #     )
        #
        #     performances = request.env['employee.performance'].sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        #     request.session['my_performances_history'] = performances.ids[:100]
        #
        #     values.update({
        #         'performances': performances,
        #         'page_name': 'performance',
        #         'default_url': '/my/performance',
        #         'pager': pager,
        #     })
        #     return request.render("employee_performance.portal_my_performances", values)
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        domain = [('employee_id', '=', employee.id)]

        # pager
        performances_count = request.env['employee.performance'].search_count(domain)
        pager = portal_pager(
            url="/my/performance",
            total=performances_count,
            page=page,
            step=self._items_per_page
        )

        performances = request.env['employee.performance'].sudo().search(domain, limit=self._items_per_page,
                                                                         offset=pager['offset'])
        request.session['my_performances_history'] = performances.ids[:100]

        values.update({
            'performances': performances,
            'page_name': 'performance',
            'default_url': '/my/performance',
            'pager': pager,
        })
        return request.render("employee_performance.portal_my_performances", values)


    @http.route(['/performance/editable/<int:performance_id>'], type='http', auth="user", website=True)
    def editable_performance(self, page=1, sortby=None, search=None, search_in='content', **kw):
        return request.render("employee_performance.edit_performance", {
            'performance' : request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        })

    @http.route(['/performance/view/<int:performance_id>'], type='http', auth="user", website=True)
    def view_performance(self, page=1, sortby=None, search=None, search_in='content', **kw):
        return request.render("employee_performance.view_performance", {
            'performance' : request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        })

    @http.route(['/performance/edit/'], type='http', auth="user", website=True)
    def edit_performance_request(self, page=1, sortby=None, search=None, search_in='content', **kw):
        performance_id = request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        key_performance_ids = request.env['key.performance'].sudo().search([('performance_id', '=', int(performance_id)),('display_type', 'not in', ['line_section','line_note'])])
        for performance in key_performance_ids:
            rate = '%s_%d' % ('employee_rate', performance.id)
            emp_rate = kw[rate] != '' and float(kw[rate]) or ''
            employee_rm = '%s_%d' % ('employee_remark', performance.id)
            employee_remark = kw[employee_rm]
            performance.sudo().write({'employee_rate': emp_rate,'employee_remark': employee_remark})
        return request.render("employee_performance.tender_success")

    @http.route(['/teamperformance/editable/<int:performance_id>'], type='http', auth="user", website=True)
    def editable_team_performance(self, page=1, sortby=None, search=None, search_in='content', **kw):
        return request.render("employee_performance.edit_team_performance", {
            'performance': request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        })

    @http.route(['/teamperformance/view/<int:performance_id>'], type='http', auth="user", website=True)
    def view_team_performance(self, page=1, sortby=None, search=None, search_in='content', **kw):
        return request.render("employee_performance.view_team_performance", {
            'performance': request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        })

    @http.route(['/teamperformance/edit/'], type='http', auth="user", website=True)
    def edit_team_performance_request(self, page=1, sortby=None, search=None, search_in='content', **kw):
        performance_id = request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        key_performance_ids = request.env['key.performance'].sudo().search(
            [('performance_id', '=', int(performance_id)), ('display_type', 'not in', ['line_section', 'line_note'])])
        competencies_ids = request.env['key.competencies'].sudo().search([('performance_id', '=', int(performance_id)),('display_type', 'not in', ['line_section','line_note'])])
        for performance in key_performance_ids:
            rate = '%s_%d' % ('manager_rate', performance.id)
            emp_rate = kw[rate] != '' and float(kw[rate]) or ''
            employee_rm = '%s_%d' % ('manager_remark', performance.id)
            employee_remark = kw[employee_rm]
            performance.sudo().write({'manager_rate': emp_rate, 'manager_remark': employee_remark})
        for competencie in competencies_ids:
            comp_rate = '%s_%d' % ('competencies_rate', competencie.id)
            competencies_rate = kw[comp_rate] != '' and float(kw[comp_rate]) or ''
            comp_comment = '%s_%d' % ('competencies_comment', competencie.id)
            competencies_comment = kw[comp_comment]
            competencie.sudo().write({'score': competencies_rate,'comment': competencies_comment})
        return request.render("employee_performance.tender_success")

    @http.route(['/performance/delete/'], type='http', auth="user", website=True)
    def delete_performance_request(self, page=1, sortby=None, search=None, search_in='content', **kw):
            performance_id = request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
            performance_id.unlink()
            return request.redirect("/my/performance")

    @http.route(['/performance/readonly/<int:performance_id>'], type='http', auth="user", website=True)
    def view_performance_request(self, page=1, sortby=None, search=None, search_in='content', **kw):
        return request.render("employee_performance.view_performance", {
            'performance': request.env['employee.performance'].sudo().browse(int(kw['performance_id']))
        })