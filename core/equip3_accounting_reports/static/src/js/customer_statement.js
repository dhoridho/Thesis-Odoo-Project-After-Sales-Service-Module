odoo.define('equip3_accounting_reports.customer_statement', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var data_statement = []

    window.click_num = 0;
    var CustomerStatement = AbstractAction.extend({
    template: 'CustomerStatementTemp',
        events: {
            'click .parent-line': 'journal_line_click',
            'click .child_col1': 'journal_line_click',
            'click #apply_filter': 'apply_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click .pl-line': 'show_drop_down',
            'click .view-account-move': 'view_acc_move',
            'click #onButton': 'onButton',
            'click .followup-letter': 'printFollowupLetter',
            'click .send-email': 'SendFollowupLetterNew',
            'click .filter_currency': '_onFilterCurrency',
            'click .send-whatsapp': 'SendFollowupLetterNew',

        },

    _onFilterCurrency: function(ev) {
            ev.preventDefault();
            $(ev.target).parents().find('ul.o_currency_filter').find('li > a.selected').removeClass('selected');
            if ($(ev.target).is('a')) {
                $(ev.target).addClass('selected');
            }
            else {
                $(ev.target).find('a').addClass('selected');
            }
            var title = $(ev.target).parents().find('ul.o_currency_filter').find('li > a.selected').parent().attr('title');
            $('.currency_caret').text(title);
        },

    printFollowupLetter: function(e) {
        e.preventDefault();
        var partner_id = $(e.target).data("partner_id");
        var partner_name = $(e.target).data("target");
        var self = this;
        self._rpc({
            model: 'customer.statement',
            method: 'view_report',
            args: [
                [self.wizard_id]
            ],
        }).then(function(data) {
            const report_data = data['report_lines']
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'equip3_accounting_reports.customer_statement',
                'report_file': 'equip3_accounting_reports.customer_statement',
                'data': {
                    'report_data': report_data[partner_id]
                },
                'context': {
                    'active_model': 'customer.statement',
                    'potrait': 1,
                    'customer_statement_pdf_report': true
                },
                'display_name': 'Customer Statement',
            };
            return self.do_action(action);
        });
    },

    SendFollowupLetterNew: function(e){
        e.preventDefault();
        var partner_id = $(e.target).data("real_partner_id");
        var self = this;
        self._rpc({
            model: 'customer.statement',
            method: 'get_mail_template',
            args : [[self.wizard_id], partner_id],
        }).then(function(result){
            if(result){
                var action = {
                    'name': _('Customer Statement'),
                    'type' : 'ir.actions.act_window',
                    'view_type' : 'form',
                    'view_mode' : 'form',
                    'res_model' : 'mail.compose.message',
                    'views' : [
                        [false, 'form']
                    ],
                    'view_id' : false,
                    'target' : 'new',
                    'context' : result['context'],
                }
                return self.do_action(action);
            }
        });
    },

    SendFollowupLetter: function (e){
        e.preventDefault();
        var partner_id = $(e.target).data("partner_id");
        var partner_name = $(e.target).data("target");
        var self = this;
        self._rpc({
            model: 'customer.statement',
            method: 'view_report',
            args: [
                [self.wizard_id]
            ],
        }).then(function(data) {
            const report_data = data['report_lines'];
            const report_email = report_data[partner_id];
            var subject = 'subject';
            var temp = report_email['overdue_template'].replace(/(\r\n|\n|\r)/gm, "<br>");
            let td = "";
            for (let x of report_email['lines']) {
                td += '<tr class="trcustom">\
                           <td>' + x['move_name'] + '</td>\
                           <td>' + x['date'] + '</td>\
                           <td>' + x['due_date'] + '</td>\
                           <td>' + x['communication'] + '</td>\
                           <td style="text-align:right;">' + x['balance'] + '</td>\
                       </tr>'
            }
            var tb = '<br>\
                      <table style="width:90%;margin:0px auto;" class="table table-condensed">\
                          <thead>\
                              <tr class="trcustom" style="padding-left:20px; border-bottom: 3px double #ddd;">\
                                  <th>Reference Number</th>\
                                  <th>Date</th>\
                                  <th>Date Due</th>\
                                  <th>Communication</th>\
                                  <th style="text-align:right;">Total Due</th>\
                              </tr>\
                          </thead>\
                          <tbody> '+ td + '<tr style="padding-left:20px; border-top: 3px double #ddd;">\
                              <td colspan="4" style="text-align:right;">\
                                  Total Overdue\
                              </td>\
                              <td style="text-align:right;">' + report_email['total_amount_residual'] + '</td>\
                          </tr>\
                          </tbody>\
                      </table>\
                      <br><br>';
            
            var action = {
                        'name': _('Customer Statement'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'mail.compose.message',
                        'views': [
                            [false, 'form']
                        ],
                        'view_id': false,
                        'target': 'new',
                        'context': {
                                    'default_partner_ids': [report_email['partner_id']],
                                    'default_body': temp + tb,
                                    'default_subject': _('Customer Statement ' + report_email['partner_name']),
                                },
                        }
            return self.do_action(action);
        });
    },

        init: function(parent, action) {
                this._super(parent, action);
                this.currency=action.currency;
                this.report_lines = action.report_lines;
                this.wizard_id = action.context.wizard | null;
            },

        start: function() {
            var self = this;
            self.initial_render = true;
            rpc.query({
                model: 'customer.statement',
                method: 'create',
                args: [{
                }]
            }).then(function(t_res) {
                self.wizard_id = t_res;
                self.load_data(self.initial_render);
            })
        },

        load_data: function (initial_render = true) {
            var self = this;
                self.$(".categ").empty();
                $('div.o_action_manager').css('overflow-y', 'auto');
                try{
                    var self = this;
                    self._rpc({
                        model: 'customer.statement',
                        method: 'view_report',
                        args: [[this.wizard_id]],
                    }).then(function(datas) {
                        _.each(datas['report_lines'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                        });
                        if (initial_render) {
                            self.$('.filter_view_tb').html(QWeb.render('CustomerStatementFilterView', {
                                filter_data: datas['filters'],
                            }));
                            self.$el.find('.partners').select2({
                            placeholder: 'Partners...',
                            });
                            self.$el.find('.companies').select2({
                            placeholder: 'Companies...',
                            });
                        }
                        var child=[];
                        self.$('.table_view_tb').html(QWeb.render('CustomerStatementTable', {
                            report_lines : datas['report_lines'],
                            filter : datas['filters'],
                            currency : datas['currency']
                        }));
                        data_statement = datas
                    });

                }
                catch (el) {
                    window.location.href
                }
            },

            format_currency: function(currency, amount) {
                if (typeof(amount) != 'number') {
                    amount = parseFloat(amount);
                }
                var formatted_value = (parseFloat(amount)).toLocaleString(currency[2],{
                    minimumFractionDigits: 2
                })
                return formatted_value
            },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            self._rpc({
                model: 'customer.statement',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'dynamic_accounts_report.partner_ledger',
                    'report_file': 'dynamic_accounts_report.partner_ledger',
                    'data': {
                        'report_data': data
                    },
                    'context': {
                        'active_model': 'customer.statement',
                        'landscape': 1,
                        'partner_ledger_pdf_report': true
                    },
                    'display_name': 'Partner Ledger',
                };
                return self.do_action(action);
            });
        },



        print_xlsx: function() {
            var self = this;
            self._rpc({
                model: 'customer.statement',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir_actions_dynamic_xlsx_download',
                    'data': {
                         'model': 'customer.statement',
                         'options': JSON.stringify(data['filters']),
                         'output_format': 'xlsx',
                         'report_data': JSON.stringify(data['report_lines']),
                         'report_name': 'Partner Ledger',
                         'dfr_data': JSON.stringify(data),
                    },
                };
                return self.do_action(action);
            });
        },

        journal_line_click: function (el){
            click_num++;
            var self = this;
            var line = $(el.target).parent().data('id');
            return self.do_action({
                type: 'ir.actions.act_window',
                    view_type: 'form',
                    view_mode: 'form',
                    res_model: 'account.move',
                    views: [
                        [false, 'form']
                    ],
                    res_id: line,
                    target: 'current',
            });
        },

        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
                _.each(data_statement['report_lines'], function(rep_lines) {
                    _.each(rep_lines['move_lines'], function(move_line) {
                        move_line.debit = self.format_currency(data_statement['currency'],move_line.debit);
                        move_line.credit = self.format_currency(data_statement['currency'],move_line.credit);
                        move_line.balance = self.format_currency(data_statement['currency'],move_line.balance);
                    });
                });
                for (var i = 0; i < data_statement['report_lines'].length; i++) {
                    if (account_id == data_statement['report_lines'][i]['id'] ){
                        $(event.currentTarget).next('tr').find('td .pl-table-div').remove();
                        $(event.currentTarget).next('tr').find('td ul').after(
                            QWeb.render('SubSectionPL', {
                                account_data: data_statement['report_lines'][i]['move_lines'],
                            }))
                        $(event.currentTarget).next('tr').find('td ul li:first a').css({
                            'background-color': '#00ede8',
                            'font-weight': 'bold',
                        });
                    }
                }
            }
        },

        view_acc_move: function(event) {
            event.preventDefault();
            var self = this;
            var context = {};
            var show_acc_move = function(res_model, res_id, view_id) {
                var action = {
                    type: 'ir.actions.act_window',
                    view_type: 'form',
                    view_mode: 'form',
                    res_model: res_model,
                    views: [
                        [view_id || false, 'form']
                    ],
                    res_id: res_id,
                    target: 'current',
                    context: context,
                };
                return self.do_action(action);
            };
            rpc.query({
                    model: 'account.move',
                    method: 'search_read',
                    domain: [
                        ['id', '=', $(event.currentTarget).data('move-id')]
                    ],
                    fields: ['id'],
                    limit: 1,
                })
                .then(function(record) {
                    if (record.length > 0) {
                        show_acc_move('account.move', record[0].id);
                    } else {
                        show_acc_move('account.move', $(event.currentTarget).data('move-id'));
                    }
                });
        },

        onButton: function(ev) {
            ev.preventDefault();
            $('.textareainput').prop('readonly', false);
        },

        apply_filter: function(event) {
            event.preventDefault();
            var self = this;
            self.initial_render = false;
            var filter_data_selected = {};

            var partner_ids = [];
            var partner_text = [];
            var span_res = document.getElementById("partner_res")
            var partner_list = $(".partners").select2('data')
            for (var i = 0; i < partner_list.length; i++) {
            if(partner_list[i].element[0].selected === true)
            {partner_ids.push(parseInt(partner_list[i].id))
            if(partner_text.includes(partner_list[i].text) === false)
            {partner_text.push(partner_list[i].text)
            }
            span_res.value = partner_text
            span_res.innerHTML=span_res.value;
            }
            }
            if (partner_list.length == 0){
            span_res.value = ""
            span_res.innerHTML="";
            }
            filter_data_selected.partner_ids = partner_ids

            var company_ids = [];
            var company_text = [];
            var span_res = document.getElementById("company_res")
            var company_list = $(".companies").select2('data')
            for (var i = 0; i < company_list.length; i++) {
            if(company_list[i].element[0].selected === true)
            {company_ids.push(parseInt(company_list[i].id))
            if(company_text.includes(company_list[i].text) === false)
            {company_text.push(company_list[i].text)
            }
            span_res.value = company_text
            span_res.innerHTML=span_res.value;
            }
            }
            if (company_list.length == 0){
            span_res.value = ""
            span_res.innerHTML="";
            }
            filter_data_selected.company_ids = company_ids

            if ($("#date_from").val()) {
                var dateString = $("#date_from").val();
                filter_data_selected.date_from = dateString;
            }
            if ($("#date_to").val()) {
                var dateString = $("#date_to").val();
                filter_data_selected.date_to = dateString;
            }
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            if (currency_item_selected.length) {
                var currency_value = $('ul.o_currency_filter').find('li > a.selected').parent().data('value');
                filter_data_selected.report_currency_id = currency_value;
            }

            rpc.query({
                model: 'customer.statement',
                method: 'write',
                args: [
                    self.wizard_id, filter_data_selected
                ],
            }).then(function(res) {
            self.initial_render = true;
                self.load_data(self.initial_render);
            });
        },

    });
    core.action_registry.add("cust_statement", CustomerStatement);
    return CustomerStatement;
});
