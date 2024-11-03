odoo.define('equip3_accounting_reports.equity_move', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;

    window.click_num = 0;
    var FinancialRatio = AbstractAction.extend({
    template: 'EquityMoveTemp',
        events: {
            'click #apply_filter': 'apply_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click .show-gl': 'show_gl',
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click': '_onAnyWhereClick',
        },

        _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content') && !ev.target.className.includes('dropdown-item')) {
                if ($('.filter_content').css('display') != 'none') {
                    $(".filter_content").css('display', 'none');
                }
            }  
        },

        _onClickFilter: function(ev) {
            ev.preventDefault();
            if ($('.filter_content').css('display') == 'none') {
                $(".filter_content").css('display', 'block');
            } else {
                $(".filter_content").css('display', 'none');
            }
            return false;
        },

        _onFilterDate: function(ev) {
            ev.preventDefault();
            $(ev.target).parents().find('ul.o_date_filter').find('li > a.selected').removeClass('selected');
            if (!$('.o_account_reports_custom-dates').hasClass('d-none')) {
                $('.o_account_reports_custom-dates').addClass('d-none');
            }
            if ($(ev.target).is('a')) {
                $(ev.target).addClass('selected');
            }
            else {
                $(ev.target).find('a').addClass('selected');
            }
            var title = $(ev.target).parents().find('ul.o_date_filter').find('li > a.selected').parent().attr('title');
            $('.date_caret').text(title);
            var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
            custom_dates.addClass('d-none');
            var custom_comp_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-dates');
            custom_comp_dates.addClass('d-none');
            $('.date_caret_comp').text(title);
        },

        _onCustomFilter: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            $(ev.target).parents().find('ul.o_filters_menu').find('li > a.selected').removeClass('selected');
            var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
            if (custom_dates.hasClass('d-none')) {
                custom_dates.removeClass('d-none');
                $('.date_caret').text('Custom');
            } else {
                custom_dates.addClass('d-none');
            }
            var prev_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-prev');
            prev_dates.addClass('d-none');
            var last_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-last');
            last_dates.addClass('d-none');
        },

        init: function(parent, action) {
        this._super(parent, action);
                this.currency=action.currency;
                this.report_lines = action.report_lines;                
                this.wizard_id = action.context.wizard | null;
                this.account_equity_filtered = action.account_equity_filtered;
                this.account_equity = action.account_equity;
                this.account_retained_earnings = action.account_retained_earnings;
                this.account_current_earnings = action.account_current_earnings;
                this.account_prive = action.account_prive;
                this.records = action.records;
                
            },


          start: function() {
            var self = this;
            self.initial_render = true;
            rpc.query({
                model: 'account.equity.move',
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
                        model: 'account.equity.move',
                        method: 'view_report',
                        args: [[this.wizard_id]],
                    }).then(function(datas) {
                            _.each(datas['report_lines'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });

                            _.each(datas['account_equity_filtered'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });

                            _.each(datas['account_equity'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });
                            
                            _.each(datas['account_retained_earnings'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });

                            _.each(datas['account_current_earnings'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });

                            _.each(datas['account_prive'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });
                            

                            if (initial_render) {
                                    self.$('.filter_view_tb').html(QWeb.render('EquityMoveFilterView', {
                                        filter_data: datas['filters'],
                                    }));
                                    self.$el.find('.target_move').select2({
                                        placeholder: 'Target Move...',
                                    });
                            }
                            var child=[];

                        self.$('.table_view_tb').html(QWeb.render('EquityMoveTable', {

                                            report_lines : datas['report_lines'],                                            
                                            filter : datas['filters'],
                                            currency : datas['currency'],
                                            credit_total : self.format_currency(datas['currency'],datas['credit_total']),
                                            debit_total : self.format_currency(datas['currency'],datas['debit_total']),
                                            balance_total : self.format_currency(datas['currency'],datas['balance_total']),
                                            account_equity_filtered : datas['account_equity_filtered'],
                                            account_equity : datas['account_equity'],
                                            account_retained_earnings : datas['account_retained_earnings'],
                                            account_current_earnings : datas['account_current_earnings'],
                                            account_prive : datas['account_prive'],
                                            records : datas['records'],
                                            
                                        }));
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

        show_gl: function(e) {
            var self = this;
            var account_id = $(e.target).attr('data-account-id');
            var options = {
                account_ids: [account_id],
            }

                var action = {
                    type: 'ir.actions.client',
                    name: 'GL View',
                    tag: 'g_l',
                    target: 'new',
                    domain: [['account_ids','=', account_id]],
                }
                return this.do_action(action);

        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            self._rpc({
                model: 'account.equity.move',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'equip3_accounting_reports.equity_move',
                    'report_file': 'equip3_accounting_reports.equity_move',
                    'data': {
                        'report_data': data
                    },
                    'context': {
                        'active_model': 'account.equity.move',
                        'landscape': 1,
                        'equity_move_pdf_report': true
                    },
                    'display_name': 'Equity Movement',
                };
                return self.do_action(action);
            });
        },

        print_xlsx: function() {
            var self = this;
            self._rpc({
                model: 'account.equity.move',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir_actions_dynamic_xlsx_download',
                    'data': {
                            'model': 'account.equity.move',
                            'options': JSON.stringify(data['filters']),
                            'output_format': 'xlsx',
                            'report_data': JSON.stringify(data['records']),
                            'report_name': 'Equity Movement',
                            'dfr_data': JSON.stringify(data),

                    },
                };
                return self.do_action(action);
            });
        },

        apply_filter: function(event) {
            $(".active-filter, .clear-filter").css('display', 'block');
            $(".filter_content").css('display', 'none');

            event.preventDefault();
            var self = this;
            self.initial_render = false;
            var filter_data_selected = {};

            var dt;
            var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            filter_data_selected.date_from = "";
            filter_data_selected.date_to = "";
            if (list_item_selected.length) {
                var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');

                $(".date-filter").css('display', 'initial');

                if (filter_value == "this_month") {
                    dt = new Date();
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    dt.setMonth(dt.getMonth() + 1);
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "this_quarter") {
                    dt = new moment();
                    filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');
                }
                else if (filter_value == "this_financial_year") {
                    dt = new Date();
                    var year = dt.getFullYear();
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');

                }
                else if (filter_value == "last_month") {
                    dt = new Date();
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    dt.setMonth(dt.getMonth() + 1);
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "last_quarter") {
                    dt = new moment();
                    filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');
                }
                else if (filter_value == "last_year") {
                    dt = new Date();
                    var year = dt.getFullYear();
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');
                }
                else if (filter_value == "today") {
                    dt = new Date();
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "no") {
                    dt = new Date();
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                }
            }
            else if (list_item_selected.length == 0) {
                dt = new Date();
                filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                if ($("#date_from").val()) {
                    var dateString = $("#date_from").val();
                    filter_data_selected.date_from = dateString;
                }
                if ($("#date_to").val()) {
                    var dateString = $("#date_to").val();
                    filter_data_selected.date_to = dateString;
                }
            }

            if ($(".target_move").length) {
                var post_res = document.querySelectorAll("[id='post_res']")
                filter_data_selected.target_move = $(".target_move")[1].value
                for (var i = 0; i < post_res.length; i++) {
                    post_res[i].value = $(".target_move")[1].value
                    post_res[i].innerHTML = post_res[i].value;
                    if ($(".target_move")[1].value == "") {
                        post_res[i].innerHTML = "posted";
                    }
                }
            }

            if (filter_data_selected.target_move != "Posted") {
                $(".target-move-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'account.equity.move',
                method: 'write',
                args: [
                    self.wizard_id, filter_data_selected
                ],
            }).then(function(res) {
            self.initial_render = false;
                self.load_data(self.initial_render);
            });
        },

        clear_filter: function (event){
            event.preventDefault();
            var self = this;
            $(".active-filter, .active-filter a, .clear-filter").css('display', 'none');

            var filter_data_selected = {};

            $('.filter_date[data-value="this_month"]').click();

            var post_res = document.querySelectorAll("[id='post_res']")
            for (var i = 0; i < post_res.length; i++) {
                post_res[i].value = "Posted"
                post_res[i].innerHTML = "Posted"
            }
            var entries_selection = document.getElementById('entries');
            for (var i = 0; i < entries_selection.options.length; i++) {
                entries_selection.options[i].selected = false;
            }
            filter_data_selected.target_move = "Posted"

            var search_choice = document.querySelectorAll(".select2-search-choice")
            for (var i = 0; i < search_choice.length; i++) {
                search_choice[i].remove()
            }
            var chosen = document.querySelectorAll(".select2-chosen")
            for (var i = 0; i < chosen.length; i++) {
                chosen[i].value = ""
                chosen[i].innerHTML = ""
            }

            var dt;
            dt = new Date();
            dt.setDate(1);
            filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');

            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);
            filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');


            rpc.query({
                model: 'account.equity.move',
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
    core.action_registry.add("e_m", FinancialRatio);
    return FinancialRatio;
});