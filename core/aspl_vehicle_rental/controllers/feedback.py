# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from datetime import date
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

list_ans = []


class FeedbackMultipage(CustomerPortal):

    @http.route(['/start_feedback/', '/start_feedback/page/<int:page>'], type='http', auth='public', website=True, csrf=False)
    def start_feedback(self, page=1, **kw):
        if request.session.get('question_number'):
            question_number = request.session.get('question_number')
        else:
            question_number = 1.
        values = {}
        IrDefault = request.env['ir.default'].sudo()
        if request.session.get('product_feedback_template'):
            feedback_template_id = int(request.session.get('product_feedback_template').get('template'))
        else:
            feedback_template_id = IrDefault.get('res.config.settings', "feedback_template_id")
        if feedback_template_id:
            feedback_template = request.env['aspl.feedback.template'].sudo().search([('id', '=', feedback_template_id)])
            if not feedback_template.question_ids:
                values.update({'error': 'There are no any question in this template'})
            request.session['feedback_template'] = feedback_template.id
            feedback_template = request.env['aspl.feedback.template'].sudo().search(
                [('id', '=', feedback_template_id)])
            request.session['feedback_template'] = feedback_template.id
            values.update({'feedback_template': feedback_template})
            return request.render('aspl_vehicle_rental.customer_feedback_system_single_question_template', values)


class CustomerFeedback(http.Controller):

    @http.route(['/customer_feedback', '/customer_feedback/<int:template>'], type='http', auth="public", website=True)
    def customer_feedback(self, **kw):
        request.session['product_feedback_template'] = {}
        if kw.get('template'):
            request.session['product_feedback_template'] = kw
        return request.render('aspl_vehicle_rental.customer_feedback_system_template')

    @http.route('/submit_feedback', type='http', auth='public', website=True, csrf=False)
    def submit_feedback(self, **kw):
        if kw.get('question_number'):
            request.session['question_number'] = int(kw.get('question_number').split('.')[0])
        values = {}
        feedback_template = request.env['aspl.feedback.template'].browse(request.session['feedback_template'])
        if feedback_template.page_configuration == 'single_page':
            request.session['feedback_list'] = []

        customer_answer_list = []
        customer_answer = {}
        group_lst = []
        feedback_obj = request.env['aspl.customer.feedback']
        for each_question in kw:
            if 'rate' in each_question:
                rate = each_question.split('-')
                customer_answer[each_question] = {'question_id': int(rate[1]),
                                                  'template_id': request.session.get('feedback_template'),
                                                  'ratings': str(kw.get(each_question))}
            elif 'radio' in each_question:
                rate_radio = each_question.split('-')
                customer_answer[each_question] = {'question_id': int(rate_radio[1]),
                                                  'template_id': request.session.get('feedback_template'),
                                                  'ratings': str(kw.get(each_question))}

            elif 'comment' in each_question:
                comment = each_question.split('-')
                customer_answer[each_question] = {'question_id': int(comment[1]),
                                                  'template_id': request.session.get('feedback_template'),
                                                  'comment': kw.get(each_question)}
            elif 'group' in each_question:
                answer = each_question.split('-')
                if customer_answer:
                    group_id = request.env['aspl.feedback.answer'].sudo().browse(int(answer[1])).id
                    if answer[0] not in customer_answer.keys():
                        group_lst.append(group_id)
                        customer_answer[answer[0]] = {'question_id': int(kw.get(each_question)),
                                                      'template_id': request.session.get('feedback_template'),
                                                      'answer_ids': [(6, 0, group_lst)]}

                    else:
                        if group_lst:
                            new_group_id = request.env['aspl.feedback.answer'].sudo().browse(int(answer[1])).id
                            if new_group_id:
                                group_lst.append(new_group_id)
                        customer_answer[answer[0]]['answer_ids'].append((6, 0, group_lst))

            elif 'question_number' not in each_question \
                    and 'submit' not in each_question \
                    and 'comment' not in each_question and \
                    'rate' not in each_question and 'final_submit' not in each_question:
                customer_answer[each_question] = {'question_id': each_question,
                                                  'template_id': request.session.get('feedback_template'),
                                                  'answer_ids': [(6, 0, kw.get(each_question))]}

        customer_answer_list.append(customer_answer)
        feedback_list = []
        for answer in customer_answer_list:
            for each in answer:
                feedback_list.append((0, 0, answer[each]))
                list_ans.append((0, 0, answer[each]))
        feedback_template = request.env['aspl.feedback.template'].sudo().browse(
            request.session.get('feedback_template'))

        if feedback_template.page_configuration == 'single_page':
            values.update({'partner_id': request.env.user.partner_id.id,
                           'feedback_date': date.today(),
                           'template_id': request.session.get('feedback_template'),
                           'customer_answer_ids': feedback_list
                           })
            request.session['feedback_values'] = values

            feedback_obj.sudo().create(values)
            return request.render('aspl_vehicle_rental.customer_feedback_submit_template', kw)
        request.session['feedback_values'] = values

    @http.route('/create_customer', type='http', auth='public', website=True, csrf=False)
    def create_customer(self, **kw):
        if kw.get('email'):
            partner_id = request.env['res.partner'].sudo().search([('email', '=', kw.get('email'))])
            if not partner_id:
                partner_id = request.env['res.partner'].sudo().create(kw)
        if request.session.get('feedback_values')['partner_id']:
            request.session.get('feedback_values')['partner_id'] = partner_id.id
        request.env['aspl.customer.feedback'].sudo().create(request.session.get('feedback_values'))
        return request.render('aspl_vehicle_rental.customer_feedback_submit_template')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
