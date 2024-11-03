odoo.define('equip3_accounting_reports.cash_flow_statement', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var reportdata = [];
    var sessionStorage = window.sessionStorage;

    window.click_num = 0;
    var CashFlow = AbstractAction.extend({
    template: 'CF_statementTemp',
        events: {
            'click .parent-line': 'journal_line_click',
            'click .child_col1': 'journal_line_click',
            'click #apply_filter': 'apply_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click .cf-line': 'get_move_lines',
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click .o_add_custom_filter_prev': '_onPrevFilter',
            'click .o_add_custom_filter_last': '_onLastFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click .cf-line': 'show_drop_down',
            'click #collapse-button': 'collapse_all',
            'click': '_onAnyWhereClick',
            'click .btn-sort-line': 'onClickSortLine',
            'click .show-gl': 'show_gl',
        },

        onClickSortLine: function(ev) {
            ev.preventDefault();
            var self = this;
            var sort = ev.currentTarget.dataset.sort;
            var sort_type = false;

            if ($(ev.currentTarget).hasClass('fa-sort') || $(ev.currentTarget).hasClass('fa-sort-up')) {
                sort_type = 'asc'
            } else {
                sort_type = 'desc'
            }

            // var obj = JSON.parse(sessionStorage.getItem('reportdata'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('reportdata')));
            var cf_line = $(ev.currentTarget).closest('tr.collapse').siblings('.cf-line');

            var list_fields = ['list_sum_cf_statement', 'list_cf_investing', 'list_cf_finance', 'list_cf_unclass', 'list_sum_all_cf_statement', 'list_cf_beginning_period', 'list_cf_closing_period']
            if (obj['type_report'] == 'indirect') {
                list_fields.push('list_cf_operating_addition', 'list_cf_operating_deduction', 'list_cf_operating_cashin_indirect', 'list_cf_operating_cashout_indirect', 'list_net_income')
            } else {
                list_fields.push('list_received_customer', 'list_cash_received', 'list_payment_supplier', 'list_cash_paid')
            }

            _.each(obj['list_previews'], function(preview) {
                _.each(list_fields, function(field) {
                    ((obj[field])[preview])['report_lines_account'].sort(function(a, b) {
                        if (sort_type == 'asc') {
                            if (sort == 'name') {
                                return (a[sort].toLowerCase() > b[sort].toLowerCase()) ? 1 : ((a[sort].toLowerCase() < b[sort].toLowerCase()) ? -1 : 0);
                            } else {
                                return (a[sort] > b[sort]) ? 1 : ((a[sort] < b[sort]) ? -1 : 0);
                            }
                        } else {
                            if (sort == 'name') {
                                return (b[sort].toLowerCase() > a[sort].toLowerCase()) ? 1 : ((b[sort].toLowerCase() < a[sort].toLowerCase()) ? -1 : 0);
                            } else {
                                return (b[sort] > a[sort]) ? 1 : ((b[sort] < a[sort]) ? -1 : 0);
                            }
                        }
                    });
                })
            });

            _.each(obj['list_previews'], function(preview) {
                _.each(list_fields, function(field) {
                    _.each(((obj[field])[preview])['report_lines_account'], function(rep_lines) {
                        rep_lines.debit = self.format_currency(obj['currency'],rep_lines.debit);
                        rep_lines.credit = self.format_currency(obj['currency'],rep_lines.credit);
                        rep_lines.balance = self.format_currency(obj['currency'],rep_lines.balance);
                    });
                })
            });

            _.each(cf_line, function(line) {
                var account_id = $(line).data('account-id');
                var classfield = 'balance';

                if ($(line).hasClass('debit')) {
                    classfield = 'debit';
                } else if ($(line).hasClass('credit')) {
                    classfield = 'credit';
                } else {
                    classfield = 'balance';
                }

                $(line).next('tr').find('td .cf-table-div').remove();
                $(line).next('tr').find('td ul').after(
                    QWeb.render('SubSectionCF', {
                        cf_name: account_id,
                        classfield: classfield,
                        account_data: obj[account_id],
                        currency : obj['currency'],
                        list_previews: obj['list_previews'],
                    }))
                $(line).next('tr').find('td ul li:first xx').css({
                    'background-color': '#00ede8',
                    'font-weight': 'bold',
                });
            });

            if (sort_type == 'asc') {
                $(`.btn-sort-line[data-sort=${sort}]`).removeClass('fa-sort fa-sort-up').addClass('fa-sort-down').css('color','black');
            } else if (sort_type == 'desc') {
                $(`.btn-sort-line[data-sort=${sort}]`).removeClass('fa-sort-down').addClass('fa-sort-up').css('color','black');
            }
        },

        _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content') && !ev.target.className.includes('dropdown-item') && !ev.target.className.includes('o_input')) {
                if ($('.filter_content').css('display') != 'none') {
                    $(".filter_content").css('display', 'none');
                }
            }  
        },

        collapse_all: function(event) {
            event.preventDefault();
            var self = this;
            var action_title = self._title;
            var classfield = 'balance';
            var data_cash_flow = JSON.parse(LZString.decompressFromUTF16(reportdata));
            var type_report = $('#type_report_res').text()
            if (type_report == 'Indirect') {
                var list_fields = ['.zz_list_net_income', '.zz_list_cf_operating_addition', '.zz_list_cf_operating_deduction', '.zz_list_cf_operating_cashin_indirect', '.zz_list_cf_operating_cashout_indirect', '.zz_list_sum_cf_statement', '.zz_list_cf_investing_cashin', '.zz_list_cf_investing_cashout', '.zz_list_cf_investing_total', '.zz_list_cf_finance_cashin', '.zz_list_cf_finance_cashout', '.zz_list_cf_finance_total', '.zz_list_cf_unclass_cashin', '.zz_list_cf_unclass_cashout', '.zz_list_cf_unclass_total', '.zz_list_sum_all_cf_statement', '.zz_list_cf_beginning_period', '.zz_list_cf_closing_period']
            } else {
                var list_fields = ['.zz_list_received_customer', '.zz_list_cash_received', '.zz_list_payment_supplier', '.zz_list_cash_paid', '.zz_list_sum_cf_statement', '.zz_list_cf_investing_cashin', '.zz_list_cf_investing_cashout', '.zz_list_cf_investing_total', '.zz_list_cf_finance_cashin', '.zz_list_cf_finance_cashout', '.zz_list_cf_finance_total', '.zz_list_cf_unclass_cashin', '.zz_list_cf_unclass_cashout', '.zz_list_cf_unclass_total', '.zz_list_sum_all_cf_statement', '.zz_list_cf_beginning_period', '.zz_list_cf_closing_period']
            }
            if ($(event.currentTarget).hasClass('collapse-all')){
                for (var i = 0; i < list_fields.length; i++) {
                    var target = $(event.currentTarget).parents().find(list_fields[i]);
                    var cf_data = $(target).data('account-id')
                    if (cf_data != undefined) {
                        if ($(target).hasClass('debit')) {
                            classfield = 'debit';
                        }
                        else if ($(target).hasClass('credit')) {
                            classfield = 'credit';
                        }
                        else {
                            classfield = 'balance';
                        }
                        $(target).find('td.parent_'+cf_data+'_'+classfield).css({'visibility': 'hidden'});
                        $(target).find('td.parent_'+cf_data).css({'visibility': 'hidden'});
                        $(target).next('tr').find('td .cf-table-div').remove();
                        $(target).next('tr').find('td ul').after(
                            QWeb.render('SubSectionCF', {
                                cf_name: cf_data,
                                classfield: classfield,
                                account_data: data_cash_flow[cf_data],
                                currency : data_cash_flow['currency'],
                                list_previews: data_cash_flow['list_previews'],
                            }))
                        $(target).next('tr').find('td ul li:first xx').css({
                            'background-color': '#00ede8',
                            'font-weight': 'bold',
                        });
                        $(target).removeClass('collapsed');
                        $(target).next('tr').addClass('show');
                    }
                }
            }else{
                for (var i = 0; i < list_fields.length; i++) {
                    var target = $(event.currentTarget).parents().find(list_fields[i]);
                    var cf_data = $(target).data('account-id')
                    if (cf_data != undefined) {
                        $(target).addClass('collapsed');
                        $(target).next('tr').removeClass('show');
                        if ($(target).hasClass('debit')) {
                            classfield = 'debit';
                        }
                        else if ($(target).hasClass('credit')) {
                            classfield = 'credit';
                        }
                        else {
                            classfield = 'balance';
                        }
                        $(target).find('td.parent_'+cf_data+'_'+classfield).css({'visibility': 'visible'});
                        $(target).find('td.parent_'+cf_data).css({'visibility': 'visible'});
                    }
                }
            }
            if ($(event.currentTarget).hasClass('collapse-all')){
                $(event.currentTarget).removeClass('collapse-all');
                $(event.currentTarget).addClass('collapsed-all');
                $(event.currentTarget).text('Collapse');
            }else{
                $(event.currentTarget).removeClass('collapsed-all');
                $(event.currentTarget).addClass('collapse-all');
                $(event.currentTarget).text('Expand');
            }
        },

        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var cf_data = $(event.currentTarget).data('account-id');
            var offset = 0;
            var data_cash_flow = JSON.parse(LZString.decompressFromUTF16(reportdata));
            var td = $(event.currentTarget).next('tr').find('td');
            var classfield = 'balance';
            if ($(event.currentTarget).hasClass('debit')) {
                classfield = 'debit';
            }
            else if ($(event.currentTarget).hasClass('credit')) {
                classfield = 'credit';
            }
            else {
                classfield = 'balance';   
            }
            if (td.length == 1) {
                $(event.currentTarget).next('tr').find('td .cf-table-div').remove();
                $(event.currentTarget).next('tr').find('td ul').after(
                    QWeb.render('SubSectionCF', {
                        cf_name: cf_data,
                        classfield: classfield,
                        account_data: data_cash_flow[cf_data],
                        currency : data_cash_flow['currency'],
                        list_previews: data_cash_flow['list_previews'],
                    }))
                $(event.currentTarget).next('tr').find('td ul li:first xx').css({
                    'background-color': '#00ede8',
                    'font-weight': 'bold',
                });
            }
            var fr_line = $(event.currentTarget).hasClass('collapsed');
            if (fr_line) {
                $(event.currentTarget).find('td.parent_'+cf_data+'_'+classfield).css({'visibility': 'hidden'});
                $(event.currentTarget).find('td.parent_'+cf_data).css({'visibility': 'hidden'});
            }else {
                $(event.currentTarget).find('td.parent_'+cf_data+'_'+classfield).css({'visibility': 'visible'});
                $(event.currentTarget).find('td.parent_'+cf_data).css({'visibility': 'visible'});
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

        _onPrevFilter: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var self = this;
            var action_title = self._title;
            $(ev.target).parents().find('ul.o_filters_comp_menu').find('li > a.selected').removeClass('selected');
            var prev_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-prev');
            if (prev_dates.hasClass('d-none')) {
                prev_dates.removeClass('d-none');
                $('.date_caret_comp').text('Previeous Period');
                var title = $(ev.target).parents().find('ul.o_date_filter_comp').find('li > a.selected').parent().attr('title');
                if (action_title == "Balance Sheet"){
                    $('.date_caret_comp').text('Same Date Last Month/Quarter');
                }
                if ($('.date_caret').text() == 'Custom Comp'){
                    $('.date_caret').text('today');
                };

            } else {
                prev_dates.addClass('d-none');
            }
            var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
            custom_dates.addClass('d-none');
            var last_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-last');
            last_dates.addClass('d-none');
        },
        _onLastFilter: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var self = this;
            var action_title = self._title;
            $(ev.target).parents().find('ul.o_filters_comp_menu').find('li > a.selected').removeClass('selected');
            var last_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-last');
            if (last_dates.hasClass('d-none')) {
                last_dates.removeClass('d-none');
                $('.date_caret_comp').text('Same Period Last Year');
                var title = $(ev.target).parents().find('ul.o_date_filter_comp').find('li > a.selected').parent().attr('title');
                if (action_title == "Balance Sheet"){
                    $('.date_caret_comp').text('Same Date Last Year');
                }
                if ($('.date_caret').text() == 'Custom Comp'){
                    $('.date_caret').text('today');
                };
            } else {
                last_dates.addClass('d-none');
            }
            var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
            custom_dates.addClass('d-none');
            var prev_dates = $(ev.target).parents().find('ul.o_filters_comp_menu').find('.o_account_reports_custom-prev');
            prev_dates.addClass('d-none');
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
            var filter_data_selected = {};

            var dt = new Date();
            dt.setDate(1);
            filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);
            filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
            filter_data_selected.comp_detail = "month";

            rpc.query({
                model: 'account.cash.flow.statement',
                method: 'create',
                args: [ filter_data_selected ]
            }).then(function(t_res) {
                self.wizard_id = t_res;
                self.load_data(self.initial_render);
            })
        },

        get_move_lines: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
            self._rpc({
                model: 'account.cash.flow.statement',
                method: 'view_report',
                args: [
                    [self.wizard_id]
                ],
            }).then(function(datas) {
            _.each(datas['journal_res'], function(journal_lines) {
                    _.each(journal_lines['journal_lines'], function(rep_lines) {
                        rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                        rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                        rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                    });

            });
            _.each(datas['account_res'], function(journal_lines) {
                    _.each(journal_lines['journal_lines'], function(rep_lines) {
                        rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                        rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                        rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                    });
                    _.each(journal_lines['move_lines'], function(move_lines) {
                        move_lines.total_debit = self.format_currency(datas['currency'],move_lines.total_debit);
                        move_lines.total_credit = self.format_currency(datas['currency'],move_lines.total_credit);
                        move_lines.balance = self.format_currency(datas['currency'],move_lines.balance);
                    });
            });


                    if(datas['levels']== 'detailed'){
                        $(event.currentTarget).next('tr').find('td ul').after(
                            QWeb.render('SubSectionCF', {
                                count: 3,
                                offset: 0,
                                account_data: datas['journal_res'],
                                level:datas['levels'],
                                currency : datas['currency'],
                                line_id:parseInt(event.currentTarget.attributes[3].value),
                            }))
                    }else if(datas['levels']== 'very'  || datas['levels']== false){
                            $(event.currentTarget).next('tr').find('td ul').after(
                            QWeb.render('ChildSubSectionCF', {
                                count: 3,
                                offset: 0,
                                account_data: datas['account_res'],
                                level:datas['levels'],
                                currency : datas['currency'],
                                line_id:parseInt(event.currentTarget.attributes[3].value),
                            }))
                    }

                    $(event.currentTarget).next('tr').find('td ul li:first a').css({
                        'background-color': '#00ede8',
                        'font-weight': 'bold',
                    });
                })
            }
        },


        load_data: function (initial_render = true) {
            var self = this;
                self.$(".categ").empty();
                $('div.o_action_manager').css('overflow-y', 'auto');
                try{
                    var self = this;
                    self._rpc({
                        model: 'account.cash.flow.statement',
                        method: 'view_report',
                        args: [[this.wizard_id]],
                    }).then(function(datas) {
                        // sessionStorage.setItem('reportdata', JSON.stringify(datas));
                        var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                        sessionStorage.setItem('reportdata', compressedData);

                        if (initial_render) {
                            self.$('.filter_view_tb').html(QWeb.render('Cash_statementFilterView', {
                                filter_data: datas['filters'],
                            }));
                            $('.filter_date[data-value="this_month"]').click();
                            self.$el.find('.journals').select2({
                                placeholder: 'Select Journals...',
                            });
                            self.$el.find('.target_move').select2({
                                placeholder: 'Target Move...',
                            });
                            self.$el.find('.levels').select2({
                                placeholder: 'Levels...',
                            });
                            self.$el.find('.companies').select2({
                                placeholder: 'Companies...',
                            });
                            self.$el.find('.type_report').select2({
                                placeholder: 'Type...',
                            });
                        }

                        _.each(datas['list_previews'], function(preview) {
                            if (datas['type_report'] == 'indirect') {
                                self.$('#report_title').html('Cash Flow Report (Indirect)')
                                
                                _.each(((datas['list_cf_operating_addition'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                                });
                                _.each(((datas['list_cf_operating_deduction'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                                });
                                _.each(((datas['list_cf_operating_cashin_indirect'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                                });
                                _.each(((datas['list_cf_operating_cashout_indirect'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                                });
                                _.each(((datas['list_net_income'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                                });
                            } else {
                                self.$('#report_title').html('Cash Flow Report (Direct)')

                                _.each(((datas['list_received_customer'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                                });
                                _.each(((datas['list_cash_received'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                                });
                                _.each(((datas['list_payment_supplier'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                                });
                                _.each(((datas['list_cash_paid'])[preview])['report_lines_account'], function(rep_lines) {
                                    rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                    rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                    rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                                });
                            }
                            
                            _.each(((datas['list_sum_cf_statement'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                            
                            _.each(((datas['list_cf_investing'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                            _.each(((datas['list_cf_finance'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                            _.each(((datas['list_cf_unclass'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                            _.each(((datas['list_sum_all_cf_statement'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                            _.each(((datas['list_cf_beginning_period'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                            _.each(((datas['list_cf_closing_period'])[preview])['report_lines_account'], function(rep_lines) {
                                rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                                rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                                rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);                       
                            });
                        });

                        _.each(datas['fetched_data'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['received_customer'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['cash_received'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['payment_supplier'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['cash_paid'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['sum_cf_statement'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['cf_investing'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['cf_finance'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });

                        _.each(datas['cf_unclass'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });
                        
                        _.each(datas['sum_all_cf_statement'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });
                        
                        _.each(datas['cf_beginning_period'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });
                        
                        _.each(datas['cf_closing_period'], function(rep_lines) {
                            rep_lines.total_debit = self.format_currency(datas['currency'],rep_lines.total_debit);
                            rep_lines.total_credit = self.format_currency(datas['currency'],rep_lines.total_credit);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        });
                        self.$('.table_view_tb').html(QWeb.render('Cash_statementTable', {
                            account_data: datas['fetched_data'],                                            
                            level:datas['levels'],
                            currency : datas['currency'],
                            type_report : datas['type_report'],
                            received_customer: datas['received_customer'],
                            cash_received: datas['cash_received'],
                            payment_supplier: datas['payment_supplier'],
                            cash_paid: datas['cash_paid'],
                            cf_operating_addition: datas['cf_operating_addition'],
                            cf_operating_deduction: datas['cf_operating_deduction'],
                            cf_operating_cashin_indirect: datas['cf_operating_cashin_indirect'],
                            cf_operating_cashout_indirect: datas['cf_operating_cashout_indirect'],
                            net_income: datas['net_income'],
                            sum_cf_statement: datas['sum_cf_statement'],
                            list_cf_operating_addition: datas['list_cf_operating_addition'],
                            list_cf_operating_deduction: datas['list_cf_operating_deduction'],
                            list_cf_operating_cashin_indirect: datas['list_cf_operating_cashin_indirect'],
                            list_cf_operating_cashout_indirect: datas['list_cf_operating_cashout_indirect'],
                            list_net_income: datas['list_net_income'],
                            cf_investing: datas['cf_investing'],
                            cf_finance: datas['cf_finance'],
                            cf_unclass: datas['cf_unclass'],
                            sum_all_cf_statement: datas['sum_all_cf_statement'],
                            cf_beginning_period: datas['cf_beginning_period'],
                            cf_closing_period: datas['cf_closing_period'],
                            list_previews: datas['list_previews'],
                            list_received_customer: datas['list_received_customer'],
                            list_cash_received: datas['list_cash_received'],
                            list_payment_supplier: datas['list_payment_supplier'],
                            list_cash_paid: datas['list_cash_paid'],
                            list_sum_cf_statement: datas['list_sum_cf_statement'],
                            list_cf_investing: datas['list_cf_investing'],
                            list_cf_finance: datas['list_cf_finance'],
                            list_cf_unclass: datas['list_cf_unclass'],
                            list_sum_all_cf_statement: datas['list_sum_all_cf_statement'],
                            list_cf_beginning_period: datas['list_cf_beginning_period'],
                            list_cf_closing_period: datas['list_cf_closing_period'],
                        }));
                        // reportdata = datas
                        reportdata = LZString.compressToUTF16(JSON.stringify(datas));
                    });
                } catch (el) {
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
            // var obj = JSON.parse(sessionStorage.getItem('reportdata'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('reportdata')));
            var account_line = $(e.target).attr('account-line') ? JSON.parse($(e.target).attr('account-line')) : null;
            var options = {
                account_ids: [account_id],
            }
            var action = {
                type: 'ir.actions.client',
                name: 'GL View',
                tag: 'g_l',
                target: 'new',
                custom_data: {
                    'account_line': account_line,
                },
                domain: [['account_ids','=', account_id], 
                         ['cash_flow'], 
                         [{'account_ids' : account_id,
                           'view_report' : 'cash_flow',
                           'filters' : obj['filters']
                           }
                         ]
                        ],
            }
            return this.do_action(action);
        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            var action_title = self._title;
            // var obj = JSON.parse(sessionStorage.getItem('reportdata'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('reportdata')));
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'equip3_accounting_reports.cash_flow_statement',
                'report_file': 'equip3_accounting_reports.cash_flow_statement',
                'data': {
                    'report_data': obj
                },
                'context': {
                    'active_model': 'account.cash.flow.statement',
                    'landscape': 1,
                    'trial_pdf_report': true
                },
                'display_name': 'Cash Flow Report',
            };
            return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title;
            // var obj = JSON.parse(sessionStorage.getItem('reportdata'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('reportdata')));
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'account.cash.flow.statement',
                     'options': JSON.stringify(obj['filters']),
                     'output_format': 'xlsx',
                     'report_data': JSON.stringify(obj['report_lines']),
                     'report_name': 'Cash Flow Report',
                     'dfr_data': JSON.stringify(obj),
                },
            };
            return self.do_action(action);
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
            filter_data_selected.previous = false;
            filter_data_selected.comparison = 0;

            if ($(".levels").length){
                var level_res = document.getElementById("level_res")
                filter_data_selected.levels = $(".levels")[1].value
                level_res.value = $(".levels")[1].value
                level_res.innerHTML=level_res.value;
                if ($(".levels").value==""){
                type_res.innerHTML="summary";
                filter_data_selected.type = "Summary"
                }
            }

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
                    filter_data_selected.comp_detail = "month";
                }
                else if (filter_value == "this_quarter") {
                    dt = new moment();
                    filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "quarter";
                }
                else if (filter_value == "this_financial_year") {
                    dt = new Date();
                    var year = dt.getFullYear();
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "year";

                }
                else if (filter_value == "last_month") {
                    dt = new Date();
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    dt.setMonth(dt.getMonth() + 1);
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "lastmonth";
                }
                else if (filter_value == "last_quarter") {
                    dt = new moment();
                    filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "lastquarter";
                }
                else if (filter_value == "last_year") {
                    dt = new Date();
                    var year = dt.getFullYear();
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "lastyear";
                }
                else if (filter_value == "today") {
                    dt = new Date();
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "today";
                }
                else if (filter_value == "no") {
                    dt = new Date();
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    filter_data_selected.comp_detail = "month";
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
                filter_data_selected.comp_detail = "custom";                
            }

            if ($("#prev").val()) {
                var prev = $("#prev").val();
                filter_data_selected.comparison = prev;
                filter_data_selected.previous = true;
                document.getElementById("last").value = null;
                document.getElementById("prev").value = null;
            }

            if ($("#last").val()) {
                var last = $("#last").val();
                filter_data_selected.comparison = last;
                filter_data_selected.previous = false;
                document.getElementById("prev").value = null;
                document.getElementById("last").value = null;
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

            if ($(".type_report").length) {
                var type_report_res = document.querySelectorAll("[id='type_report_res']")
                filter_data_selected.type_report = $(".type_report")[1].value
                for (var i = 0; i < type_report_res.length; i++) {
                    type_report_res[i].value = $(".type_report")[1].value
                    type_report_res[i].innerHTML = type_report_res[i].value;
                    if ($(".type_report")[1].value == "") {
                        type_report_res[i].innerHTML = "direct";
                    }
                }
            }

            if (filter_data_selected.target_move != "Posted") {
                $(".target-move-filter").css('display', 'initial');
            }
            if (filter_data_selected.comparison != 0) {
                $(".comparison-filter").css('display', 'initial');
            }
            if (filter_data_selected.type_report != "Direct") {
                $(".type-report-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'account.cash.flow.statement',
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


            filter_data_selected.comp_detail = "month"
            filter_data_selected.comparison = 0;

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

            filter_data_selected.previous = false;

            rpc.query({
                model: 'account.cash.flow.statement',
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
    core.action_registry.add("c_f_s", CashFlow);
    return CashFlow;
});