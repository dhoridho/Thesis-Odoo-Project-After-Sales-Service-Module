odoo.define('equip3_accounting_reports.financial_ratio', function (require) {
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
    template: 'FinancialRatioTemp',
        events: {
            'click .parent-line': 'journal_line_click',
            'click .child_col1': 'journal_line_click',
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
                this.report_lines_current_ratio = action.report_lines_current_ratio;
                this.report_lines_capital_ratio = action.report_lines_capital_ratio;
                this.report_lines_quick_ratio = action.report_lines_quick_ratio;
                this.report_lines_cash_ratio = action.report_lines_cash_ratio;
                this.report_lines_debt_to_asset_ratio = action.report_lines_debt_to_asset_ratio;
                this.report_lines_debt_to_equity_ratio = action.report_lines_debt_to_equity_ratio;
                this.report_lines_long_term_debt_to_equity_ratio = action.report_lines_long_term_debt_to_equity_ratio;
                this.report_lines_times_interest_earned_ratio = action.report_lines_times_interest_earned_ratio;
                this.report_lines_EBITDA = action.report_lines_EBITDA;
                this.report_lines_return_on_asset = action.report_lines_return_on_asset;
                this.report_lines_return_on_equity = action.report_lines_return_on_equity;
                this.report_lines_profit_margin = action.report_lines_profit_margin;
                this.report_lines_gross_profit_margin = action.report_lines_gross_profit_margin;
                this.report_lines_ar_turnover_ratio = action.report_lines_ar_turnover_ratio;
                this.report_lines_merchandise_inventory = action.report_lines_merchandise_inventory;
                this.report_lines_total_assets = action.report_lines_total_assets;
                this.report_lines_net_fixed_assets = action.report_lines_net_fixed_assets;
            },


          start: function() {
            var self = this;
            self.initial_render = true;
            rpc.query({
                model: 'account.financial.ratio',
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
                        model: 'account.financial.ratio',
                        method: 'view_report',
                        args: [[this.wizard_id]],
                    }).then(function(datas) {
                            _.each(datas['report_lines'], function(rep_lines) {
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            });

                            _.each(datas['report_lines_current_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_quick_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_capital_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_cash_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_debt_to_asset_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_debt_to_equity_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_long_term_debt_to_equity_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_times_interest_earned_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_EBITDA'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_return_on_asset'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_return_on_equity'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_profit_margin'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_gross_profit_margin'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_ar_turnover_ratio'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_merchandise_inventory'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_total_assets'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });
                            _.each(datas['report_lines_net_fixed_assets'], function(rep_lines) {
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.percen = self.format_currency(datas['currency'],rep_lines.percen);
                            });

                            if (initial_render) {
                                    self.$('.filter_view_tb').html(QWeb.render('FinancialRatioFilterView', {
                                        filter_data: datas['filters'],
                                    }));
                                    self.$el.find('.journals').select2({
                                        placeholder: 'Select Journals...',
                                    });
                                    self.$el.find('.target_move').select2({
                                        placeholder: 'Target Move...',
                                    });
                            }
                            var child=[];

                        self.$('.table_view_tb').html(QWeb.render('FinancialRatioTable', {

                                            report_lines : datas['report_lines'],                                            
                                            filter : datas['filters'],
                                            currency : datas['currency'],
                                            credit_total : self.format_currency(datas['currency'],datas['debit_total']),
                                            debit_total : self.format_currency(datas['currency'],datas['debit_total']),
                                            report_lines_current_ratio : datas['report_lines_current_ratio'],
                                            report_lines_quick_ratio : datas['report_lines_quick_ratio'],
                                            report_lines_capital_ratio : datas['report_lines_capital_ratio'],
                                            report_lines_cash_ratio : datas['report_lines_cash_ratio'],
                                            report_lines_debt_to_asset_ratio : datas['report_lines_debt_to_asset_ratio'],
                                            report_lines_debt_to_equity_ratio : datas['report_lines_debt_to_equity_ratio'],
                                            report_lines_long_term_debt_to_equity_ratio : datas['report_lines_long_term_debt_to_equity_ratio'],
                                            report_lines_times_interest_earned_ratio : datas['report_lines_times_interest_earned_ratio'],
                                            report_lines_EBITDA : datas['report_lines_EBITDA'],
                                            report_lines_return_on_asset : datas['report_lines_return_on_asset'],
                                            report_lines_return_on_equity : datas['report_lines_return_on_equity'],
                                            report_lines_profit_margin : datas['report_lines_profit_margin'],
                                            report_lines_gross_profit_margin : datas['report_lines_gross_profit_margin'],
                                            report_lines_ar_turnover_ratio : datas['report_lines_ar_turnover_ratio'],
                                            report_lines_merchandise_inventory : datas['report_lines_merchandise_inventory'],
                                            report_lines_total_assets : datas['report_lines_total_assets'],
                                            report_lines_net_fixed_assets : datas['report_lines_net_fixed_assets'],
                                        }));
                });

                    }
                catch (el) {
                    window.location.href
                    }
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
                model: 'account.financial.ratio',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'equip3_accounting_reports.financial_ratio_report',
                    'report_file': 'equip3_accounting_reports.financial_ratio_report',
                    'data': {
                        'report_data': data
                    },
                    'context': {
                        'active_model': 'account.financial.ratio',
                        'landscape': 1,
                        'financial_ratio_pdf_report': true
                    },
                    'display_name': 'Financial Ratio',
                };
                return self.do_action(action);
            });
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

        print_xlsx: function() {
            var self = this;
            self._rpc({
                model: 'account.financial.ratio',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir_actions_dynamic_xlsx_download',
                    'data': {
                         'model': 'account.financial.ratio',
                         'options': JSON.stringify(data['filters']),
                         'output_format': 'xlsx',
                         'report_data': JSON.stringify(data['report_lines']),
                         'report_name': 'Financial Ratio',
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
                model: 'account.financial.ratio',
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
            filter_data_selected.date_from = false;

            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);
            filter_data_selected.date_to = false;

            rpc.query({
                model: 'account.financial.ratio',
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
    core.action_registry.add("f_r", FinancialRatio);
    return FinancialRatio;
});