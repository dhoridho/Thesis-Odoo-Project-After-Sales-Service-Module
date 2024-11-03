odoo.define('equip3_accounting_reports.financial_reports_custom', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var bspnlline = [];
    var filterdata = {};
    var sessionStorage = window.sessionStorage;

    window.click_num = 0;
    var ProfitAndLoss = AbstractAction.extend({
    template: 'custom_dfr_template_new',
    events: {
        'click .parent-line': 'journal_line_click',
        'click .child_col1': 'journal_line_click',
        'click #apply_filter': 'apply_filter',
        'click #pdf': 'print_pdf',
        'click #xlsx': 'print_xlsx',
        'click .show-gl': 'show_gl',
        'click .filter_date': '_onFilterDate',
        'click .o_add_custom_filter': '_onCustomFilter',
        'click .o_add_custom_filter_prev': '_onPrevFilter',
        'click .o_add_custom_filter_last': '_onLastFilter',
        'click .o_add_custom_filter_customcomp': '_onCustomCompFilter',
        'click .filter_currency': '_onFilterCurrency',
        'click #apply_budget_on': '_onApplyBudgetOn',
        'click #apply_budget_off': '_onApplyBudgetOff',
        'click .fr-line': 'show_drop_down',
        'click .fr-line2': 'show_drop_down2',
        'click #o_equip_filter_dropdown': '_onClickFilter',
        'click .clear-filter': 'clear_filter',
        'click #collapse-button': 'collapse_all',
        'click': '_onAnyWhereClick',
        'click .btn-sort': 'onClickSort',
    },

    _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content') && !ev.target.className.includes('dropdown-item') && !ev.target.className.includes('o_input')) {
                if ($('.filter_content').css('display') != 'none') {
                    $(".filter_content").css('display', 'none');
                }
            }  
        },

    onClickSort: function(ev) {
        ev.preventDefault();
        var sort = ev.currentTarget.dataset.sort
        var sort_type = false

        if ($(ev.currentTarget).hasClass('fa-sort') || $(ev.currentTarget).hasClass('fa-sort-up')) {
            sort_type = 'asc'
        } else {
            sort_type = 'desc'
        }

        this.initial_render = false;
        this.load_data(this.initial_render, sort, sort_type);
    },

    collapse_all: function(event) {
        event.preventDefault();
        var self = this;
        var action_title = self._title;
        var bslinedata = JSON.parse(LZString.decompressFromUTF16(bspnlline));
        var col = 1 + bslinedata['years_preview'].length
        if (bslinedata.filters.debit_credit == 'on'){
            col = 1 + (bslinedata['years_preview'].length * 3)
        }
        if (bslinedata.filters.budget == 'on'){
            col = 1 + (bslinedata['years_preview'].length * 2)
        }
        var comp_list = bslinedata['comps_list']
        var col_total = col * comp_list.length

        bslinedata.filters.budget
        bslinedata.filters.debit_credit

        if (bslinedata.filters.consolidate == 'on' && bslinedata.filters.entities_comparison == 'on' ){
            col_total += 1
            col +=1
        }

        if ($(event.currentTarget).hasClass('collapse-all')){
            for (var i = 0; i < bslinedata['bs_lines'].length; i++) {
                if (bslinedata['bs_lines'][i]['level'] > 2){
                    if (bslinedata['bs_lines'][i]['is_parent']){
                        var acc_data = []
                        for (var j = 0; j < bslinedata['bs_lines'].length; j++) {
                            if (bslinedata['bs_lines'][i]['number_id'] == bslinedata['bs_lines'][j]['parentid']){
                                acc_data.push(bslinedata['bs_lines'][j]);
                                var target = $(event.target).parents().find('.c'+bslinedata['bs_lines'][j]['parentid']);
                                var account_id = target.data('account-id');
                                target.removeClass('collapsed');
                                target.next('tr').addClass('show');
                                target.find('td.'+account_id).css({
                                    'visibility': 'hidden',
                                });
                                target.next('tr').find('td .fr-table-div').remove();
                                target.next('tr').find('td ul').after(QWeb.render('SubSectionFR', {
                                    name : bslinedata['name'],
                                    report_lines : bslinedata['report_lines'],
                                    filter : bslinedata['filters'],
                                    currency : bslinedata['currency'],
                                    currency_symbol : bslinedata['currency_symbol'],
                                    credit_total : bslinedata['credit_total'],
                                    debit_total : bslinedata['debit_total'],
                                    debit_balance : bslinedata['debit_balance'],
                                    bs_lines : acc_data,
                                    cat_report_line : bslinedata['cat_report_line'],
                                    years_preview : bslinedata['years_preview'],
                                    filter_budget : bslinedata.filters.filter_budget,
                                    budget : bslinedata.filters.budget,
                                    debit_credit : bslinedata.filters.debit_credit,
                                    col : bslinedata['years_preview'].length,
                                    tot_column : col - 1,
                                    comps_list : bslinedata['comps_list'],
                                    comp_names : bslinedata['comp_names'],
                                    tot_comp_list : bslinedata['comps_list'].length,
                                    col_total : col_total * bslinedata['curr_list'].length,
                                    entities_comparison : bslinedata.filters.entities_comparison,
                                    all_account : bslinedata.filters.all_account,
                                    curr_list : bslinedata['curr_list'],
                                }));
                            }
                        }
                    }
                }
            }
        }else{
            for (var i = 0; i < bslinedata['bs_lines'].length; i++) {
                if (bslinedata['bs_lines'][i]['level'] > 2){
                    if (bslinedata['bs_lines'][i]['is_parent']){
                        var acc_data = []
                        for (var j = 0; j < bslinedata['bs_lines'].length; j++) {
                            if (bslinedata['bs_lines'][i]['number_id'] == bslinedata['bs_lines'][j]['parentid']){
                                acc_data.push(bslinedata['bs_lines'][j]);
                                var target = $(event.target).parents().find('.c'+bslinedata['bs_lines'][j]['parentid']);
                                var account_id = target.data('account-id');
                                target.addClass('collapsed');
                                target.next('tr').removeClass('show');
                                target.find('td.'+account_id).css({
                                    'visibility': 'visible',
                                });
                            }
                        }
                    }
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

    _onClickFilter: function(ev) {
        ev.preventDefault();
        if ($('.filter_content').css('display') == 'none') {
            $(".filter_content").css('display', 'block');
        } else {
            $(".filter_content").css('display', 'none');
        }
        return false;
    },

    show_drop_down: function(event) {
        event.preventDefault();
        var self = this;
        var action_title = self._title;
        var account_id = $(event.currentTarget).data('account-id');
        var acc_data = []
        var bslinedata = JSON.parse(LZString.decompressFromUTF16(bspnlline));
        var col = 1 + bslinedata['years_preview'].length
        if (bslinedata.filters.debit_credit == 'on'){
            col = 1 + (bslinedata['years_preview'].length * 3)
        }
        if (bslinedata.filters.budget == 'on'){
            col = 1 + (bslinedata['years_preview'].length * 2)
        }
        var comp_list = bslinedata['comps_list']
        var col_total = col * comp_list.length

        if (bslinedata.filters.consolidate == 'on' && bslinedata.filters.entities_comparison == 'on' ){
            col_total += 1
            col +=1
        }
           
        for (var i = 0; i < bslinedata['bs_lines'].length; i++) {
            if (account_id == bslinedata['bs_lines'][i]['parentid']){
                acc_data.push(bslinedata['bs_lines'][i]);
                $(event.currentTarget).next('tr').find('td .fr-table-div').remove();
                $(event.currentTarget).next('tr').find('td ul').after(
                    QWeb.render('SubSectionFR', {
                        name : bslinedata['name'],
                        report_lines : bslinedata['report_lines'],
                        filter : bslinedata['filters'],
                        currency : bslinedata['currency'],
                        currency_symbol : bslinedata['currency_symbol'],
                        credit_total : bslinedata['credit_total'],
                        debit_total : bslinedata['debit_total'],
                        debit_balance : bslinedata['debit_balance'],
                        bs_lines : acc_data,
                        cat_report_line : bslinedata['cat_report_line'],
                        years_preview : bslinedata['years_preview'],
                        filter_budget : bslinedata.filters.filter_budget,
                        budget : bslinedata.filters.budget,
                        debit_credit : bslinedata.filters.debit_credit,
                        col : bslinedata['years_preview'].length,
                        tot_column : col - 1,
                        comps_list : bslinedata['comps_list'],
                        comp_names : bslinedata['comp_names'],
                        tot_comp_list : bslinedata['comps_list'].length,
                        col_total : col_total * bslinedata['curr_list'].length,
                        entities_comparison : bslinedata.filters.entities_comparison,
                        all_account : bslinedata.filters.all_account,
                        curr_list : bslinedata['curr_list'],
                }))
            }
        }
        var fr_line = $(event.currentTarget).hasClass('collapsed');
        if (fr_line) {
            $(event.currentTarget).find('td.'+account_id).css({
                'visibility': 'hidden',
            });
        }else {
            $(event.currentTarget).find('td.'+account_id).css({
                'visibility': 'visible',
            });
        }
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
        $('.date_caret_comp').text(title);
    },

    _onCustomFilter: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        $(ev.target).parents().find('ul.o_filters_menu').find('li > a.selected').removeClass('selected');
        var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
        var comp_detail_res = document.getElementById("comp_detail_res");
        if (custom_dates.hasClass('d-none')) {
            custom_dates.removeClass('d-none');
            $('.date_caret').text('Custom');
            comp_detail_res.value = "custom";
            comp_detail_res.innerHTML = comp_detail_res.value;
        } else {
            custom_dates.addClass('d-none');
        }
        var prev_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-prev');
        prev_dates.addClass('d-none');
        var last_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-last');
        last_dates.addClass('d-none');
        var customcomp = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-customcomp');
        customcomp.addClass('d-none');
    },

    _onCustomCompFilter: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        $(ev.target).parents().find('ul.o_filters_menu_comp').find('li > a.selected').removeClass('selected');
        var custom_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-customcomp');
        var comp_detail_res = document.getElementById("comp_detail_res");
        if (custom_dates.hasClass('d-none')) {
            custom_dates.removeClass('d-none');
            $('.date_caret').text('Custom Comp');
            comp_detail_res.value = "custom_comp";
            comp_detail_res.innerHTML = comp_detail_res.value;
        } else {
            custom_dates.addClass('d-none');
        }

        var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
        custom_dates.addClass('d-none');
        var prev_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-prev');
        prev_dates.addClass('d-none');
        var last_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-last');
        last_dates.addClass('d-none');
    },

    _onPrevFilter: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var self = this;
        var action_title = self._title;
        $(ev.target).parents().find('ul.o_filters_menu_comp').find('li > a.selected').removeClass('selected');
        var prev_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-prev');
        if (prev_dates.hasClass('d-none')) {
            prev_dates.removeClass('d-none');
            $('.date_caret_comp').text('Previous Period');
            var title = $(ev.target).parents().find('ul.o_date_filter_comp').find('li > a.selected').parent().attr('title');
            var comp_detail_res = document.getElementById("comp_detail_res");
            if (action_title == "Balance Sheet"){
                $('.date_caret_comp').text('Same Date Last Month/Quarter');
            }
            if ($('.date_caret').text() == 'Custom Comp'){
                $('.date_caret').text('today');
                comp_detail_res.value = 'today';
                comp_detail_res.innerHTML = comp_detail_res.value;
            };

        } else {
            prev_dates.addClass('d-none');
        }
        var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
        custom_dates.addClass('d-none');
        var last_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-last');
        last_dates.addClass('d-none');
        var customcomp = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-customcomp');
        customcomp.addClass('d-none');
    },
    _onLastFilter: function(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var self = this;
        var action_title = self._title;
        $(ev.target).parents().find('ul.o_filters_menu_comp').find('li > a.selected').removeClass('selected');
        var last_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-last');
        if (last_dates.hasClass('d-none')) {
            last_dates.removeClass('d-none');
            $('.date_caret_comp').text('Same Period Last Year');
            var title = $(ev.target).parents().find('ul.o_date_filter_comp').find('li > a.selected').parent().attr('title');
            var comp_detail_res = document.getElementById("comp_detail_res");
            if (action_title == "Balance Sheet"){
                $('.date_caret_comp').text('Same Date Last Year');
            }
            if ($('.date_caret').text() == 'Custom Comp'){
                $('.date_caret').text('today');
                comp_detail_res.value = 'today';
                comp_detail_res.innerHTML = comp_detail_res.value;
            };
        } else {
            last_dates.addClass('d-none');
        }
        var custom_dates = $(ev.target).parents().find('ul.o_filters_menu').find('.o_account_reports_custom-dates');
        custom_dates.addClass('d-none');
        var prev_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-prev');
        prev_dates.addClass('d-none');
        var customcomp = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-customcomp');
        customcomp.addClass('d-none');
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

    _onApplyBudgetOn: function(ev) {
        ev.preventDefault();
        $(ev.target).parents().find('.btn-budget-on').addClass('o_hidden');
        $(ev.target).parents().find('.btn-budget-off').removeClass('o_hidden');
    },

    _onApplyBudgetOff: function(ev) {
        ev.preventDefault();
        $(ev.target).parents().find('.btn-budget-off').addClass('o_hidden');
        $(ev.target).parents().find('.btn-budget-on').removeClass('o_hidden');
    },

    init: function(parent, action) {
        this._super(parent, action);
        this.currency=action.currency;
        this.bs_lines = action.bs_lines;
        this.cat_report_line = action.cat_report_line;
        this.years_preview = action.years_preview;
        this.wizard_id = action.context.wizard | null;
        this.filter_budget = false;
    },
    start: function() {
        var self = this;
        self.initial_render = true;
        var filter_data_selected = {};
        rpc.query({
            model: 'ctm.dynamic.balance.sheet.report',
            method: 'create',
            args: [filter_data_selected]
        }).then(function(t_res) {
            self.wizard_id = t_res;
            self.load_data(self.initial_render);
        })
    },

    load_data: function (initial_render = true, sort=false, sort_type=false) {
        var self = this;
        var action_title = self._title;
        $('div.o_action_manager').css('overflow-y', 'auto');
        self.$(".categ").empty();
        try {
            var self = this;
            self._rpc({
                model: 'ctm.dynamic.balance.sheet.report',
                method: 'view_report',
                args: [[this.wizard_id], action_title],
                kwargs: {sort: sort, sort_type: sort_type},
            }).then(function(datas) {
                // sessionStorage.setItem('data_bs_pnl', JSON.stringify(datas));
                var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                sessionStorage.setItem('data_bs_pnl', compressedData);
                if (initial_render) {
                    self.$('.filter_view_dfr').html(QWeb.render('custom_DfrFilterView', {
                        filter_data: datas['filters'],
                        title : datas['name'],
                    }));
                    self.$el.find('.journals').select2({
                        placeholder: ' Journals...',
                    });
                    self.$el.find('.currencies').select2({
                        placeholder: ' Currencies...',
                    });
                    self.$el.find('.account').select2({
                        placeholder: ' Accounts...',
                    });
                    self.$el.find('.account-tag').select2({
                        placeholder: 'Account Tag...',
                    });
                    self.$el.find('.analytics').select2({
                        placeholder: 'Analytic Accounts...',
                    });
                    self.$el.find('.analytic-tag').select2({
                        placeholder: 'Analytic Tag...',
                    });
                    self.$el.find('.analytic-tags').select2({
                        placeholder: 'Analytic Tags...',
                    });
                    self.$el.find('.target_move').select2({
                        placeholder: 'Target Move...',
                    });
                    self.$el.find('.analytic_group_ids').select2({
                        placeholder: 'analytic_group_ids...',
                    });
                    self.$el.find('.book').select2({
                        placeholder: 'Book...',
                    });
                    self.$el.find('.consolidate').select2({
                        placeholder: 'consolidation...',
                    });
                    self.$el.find('.comp_detail').select2({
                        placeholder: 'Detail...',
                    });
                    self.$el.find('.budget').select2({
                        placeholder: 'budget...',
                    });
                    self.$el.find('.debit_credit').select2({
                        placeholder: 'Debit & Credit...',
                    });
                    self.$el.find('.entities_comparison').select2({
                        placeholder: 'Entities Comparison...',
                    });

                    self.$el.find('.all_account').select2({
                        placeholder: 'All Account...',
                    });
                    self.$el.find('.btn-budget-on').addClass('o_hidden');
                    self.$el.find('.btn-budget-off').removeClass('o_hidden');

                    if (action_title == 'Balance Sheet'){
                        var comp_detail_res = document.getElementById("comp_detail_res");
                        comp_detail_res.value = "today";
                        comp_detail_res.innerHTML = comp_detail_res.value;
                        $('.filter_date[data-value="today"]').click();
                    };

                    if (action_title == 'Profit and Loss'){
                        var comp_detail_res = document.getElementById("comp_detail_res");
                        comp_detail_res.value = "month";
                        comp_detail_res.innerHTML = comp_detail_res.value;
                        $('.filter_date[data-value="this_month"]').click();
                    };
                }
                var child=[];
                var col = 1 + datas['years_preview'].length
                if (datas.filters.debit_credit == 'on'){
                    col = 1 + (datas['years_preview'].length * 3)
                }
                if (datas.filters.budget == 'on'){
                    col = 1 + (datas['years_preview'].length * 2)
                }
                var comp_list = datas['comps_list']
                var col_total = col * comp_list.length

                if (datas['years_preview'].length == 2){
                    col_total += 1
                }

                if (datas.filters.consolidate == 'on' && datas.filters.entities_comparison == 'on' ){
                    col_total += 1
                    col +=1
                }

                if (datas.filters.analytic_group_ids) {
                    col_total += 1
                }

                var renderPromise = self.$('.table_view_dfr').html(QWeb.render('custom_dfr_table', {
                    name : datas['name'],
                    report_lines : datas['report_lines'],
                    filter : datas['filters'],
                    currency : datas['currency'],
                    currency_symbol : datas['currency_symbol'],
                    credit_total : datas['credit_total'],
                    debit_total : datas['debit_total'],
                    debit_balance : datas['debit_balance'],
                    bs_lines : datas['bs_lines'],
                    cat_report_line : datas['cat_report_line'],
                    years_preview : datas['years_preview'],
                    filter_budget : datas.filters.filter_budget,
                    budget : datas.filters.budget,
                    debit_credit : datas.filters.debit_credit,
                    tot_column : col - 1,
                    comps_list : datas['comps_list'],
                    comp_names : datas['comp_names'],
                    tot_comp_list : datas['comps_list'].length,
                    col_total : (col_total * datas['curr_list'].length),
                    entities_comparison : datas.filters.entities_comparison,
                    all_account : datas.filters.all_account,
                    curr_list : datas['curr_list'],
                }));
                // bslinedata = datas
                bspnlline = LZString.compressToUTF16(JSON.stringify(datas));

                renderPromise.promise().done(function () {
                    if (sort) {
                        if (sort_type == 'asc') {
                            $(`[data-sort=${sort}]`).removeClass('fa-sort fa-sort-up').addClass('fa-sort-down').css('color','black');
                        } else if (sort_type == 'desc') {
                            $(`[data-sort=${sort}]`).removeClass('fa-sort-down').addClass('fa-sort-up').css('color','black');
                        }
                    }
                });
                
                if ($('.collapse-all').length) {
                    $('.collapse-all').click();    
                } else {
                    $('.collapsed-all').click();
                    $('.collapse-all').click();
                }

                var table_width = 40;
                if (datas.filters.currencies.length > 2) {
                    table_width -= (datas.filters.currencies.length * 5)
                }
                else if (datas.filters.analytic_group_ids[0] == 'Branch') {
                    table_width = 25
                }
                $(".table_row_one_mode, .table_row_many_mode").css("width", `${table_width}%`);
                $(".subtotal_report_line_filter_entities_consolidate").css("min-width", "200px");
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
        var action_title = self._title;
        var account_id = $(e.target).attr('data-account-id');
        // var obj = JSON.parse(sessionStorage.getItem('data_bs_pnl'));
        var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_bs_pnl')));
        var options = {account_ids: [account_id]}
        
        var action = {
            type: 'ir.actions.client',
            name: 'GL View',
            tag: 'g_l',
            target: 'new',
            domain: [['account_ids','=', account_id],
                     [action_title], 
                     [{'account_ids' : account_id,
                       'view_report' : action_title,
                       'filters' : obj['filters'],
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
        var report_title = document.getElementById('report_title').innerHTML.replaceAll('\n', '').replaceAll(' ', '');
        self._rpc({
            model: 'ctm.dynamic.balance.sheet.report',
            method: 'view_report',
            args: [
                [self.wizard_id], action_title
            ],
        }).then(function(data) {
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'equip3_accounting_reports.balance_sheet',
                'print_report_name': action_title,
                'report_file': 'equip3_accounting_reports.balance_sheet',
                'data': {
                    'report_data': data,
                    'report_name': report_title
                },
                'context': {
                    'active_model': 'ctm.dynamic.balance.sheet.report',
                    'landscape': 1,
                    'bs_report': true
                },
                'display_name': action_title,
            };
            return self.do_action(action);
        });
    },

    print_xlsx: function() {
        var self = this;
        var action_title = document.getElementById('report_title').innerHTML.replaceAll('\n', '').replaceAll(' ', '');
        self._rpc({
            model: 'ctm.dynamic.balance.sheet.report',
            method: 'view_report',
            args: [
                [self.wizard_id],  self._title
            ],
        }).then(function(data) {
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'ctm.dynamic.balance.sheet.report',
                     'options': JSON.stringify(data['filters']),
                     'output_format': 'xlsx',
                     'report_data': self._title,
                     'report_name': action_title,
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
        var action_title = self._title;
        self.initial_render = false;
        var filter_data_selected = {};
        filter_data_selected.comparison = null;
        filter_data_selected.previous = null;

        var account_ids = [];
        var account_text = [];
        var account_res = document.querySelectorAll("[id='acc_res']")
        var account_list = $(".account").select2('data')
        for (var i = 0; i < account_list.length; i++) {
            if(account_list[i].element[0].selected === true){
                account_ids.push(parseInt(account_list[i].id))
                if(account_text.includes(account_list[i].text) === false){
                    account_text.push(account_list[i].text)
                }
                for (var j = 0; j < account_res.length; j++) {
                    account_res[j].value = account_text
                    account_res[j].innerHTML = account_res[j].value;
                }
            }
        }
        if (account_list.length == 0){
            for (var i = 0; i < account_res.length; i++) {
                account_res[i].value = ""
                account_res[i].innerHTML = "All";
            }
        }
        filter_data_selected.account_ids = account_ids

        var journal_ids = [];
        var journal_text = [];
        var journal_res = document.querySelectorAll("[id='journal_res']")
        var journal_list = $(".journals").select2('data')
        for (var i = 0; i < journal_list.length; i++) {
            if(journal_list[i].element[0].selected === true){
                journal_ids.push(parseInt(journal_list[i].id))
                if(journal_text.includes(journal_list[i].text) === false){
                    journal_text.push(journal_list[i].text)
                }
                for (var j = 0; j < journal_res.length; j++) {
                    journal_res[j].value = journal_text
                    journal_res[j].innerHTML = journal_res[j].value;
                }
            }
        }
        if (journal_list.length == 0){
            for (var i = 0; i < journal_res.length; i++) {
                journal_res[i].value = ""
                journal_res[i].innerHTML = "All";
            }
        }
        filter_data_selected.journal_ids = journal_ids

        var currency_ids = [];
        var currency_text = [];
        var currency_res = document.querySelectorAll("[id='currency_res']")
        var currency_list = $(".currencies").select2('data')
        for (var i = 0; i < currency_list.length; i++) {
            if(currency_list[i].element[0].selected === true){
                currency_ids.push(parseInt(currency_list[i].id))
                if(currency_text.includes(currency_list[i].text) === false){
                    currency_text.push(currency_list[i].text)
                }
                for (var j = 0; j < currency_res.length; j++) {
                    currency_res[j].value = currency_text
                    currency_res[j].innerHTML = currency_res[j].value;
                }
            }
        }
        if (currency_list.length == 0){
            for (var i = 0; i < currency_res.length; i++) {
                currency_res[i].value = ""
                currency_res[i].innerHTML = "All";
            }
        }
        filter_data_selected.currency_ids = currency_ids


        var account_tag_ids = [];
        var account_tag_text = [];
        var account_tag_res = document.getElementById("acc_tag_res")
        var account_tag_list = $(".account-tag").select2('data')
        for (var i = 0; i < account_tag_list.length; i++) {
            if(account_tag_list[i].element[0].selected === true){
                account_tag_ids.push(parseInt(account_tag_list[i].id))
                if(account_tag_text.includes(account_tag_list[i].text) === false){
                    account_tag_text.push(account_tag_list[i].text)
                }
                account_tag_res.value = account_tag_text
                account_tag_res.innerHTML = account_tag_res.value;
            }
        }
        if (account_tag_list.length == 0){
            account_tag_res.value = ""
            account_tag_res.innerHTML = "";
        }
        filter_data_selected.account_tag_ids = account_tag_ids

        var analytic_ids = []
        var analytic_text = [];
        var analytic_res = document.querySelectorAll("[id='analytic_res']")
        var analytic_list = $(".analytics").select2('data')
        for (var i = 0; i < analytic_list.length; i++) {
            if(analytic_list[i].element[0].selected === true){
                analytic_ids.push(parseInt(analytic_list[i].id))
                if(analytic_text.includes(analytic_list[i].text) === false){
                    analytic_text.push(analytic_list[i].text)
                }
                for (var j = 0; j < analytic_res.length; j++) {
                    analytic_res[j].value = analytic_text
                    analytic_res[j].innerHTML = analytic_res[j].value;
                }
            }
        }
        if (analytic_list.length == 0){
            for (var i = 0; i < analytic_res.length; i++) {
                analytic_res[i].value = ""
                analytic_res[i].innerHTML = "All";
            }
        }
        filter_data_selected.analytic_ids = analytic_ids

        var analytic_tag_ids = [];
        var analytic_tag_text = [];
        var analytic_tag_res = document.querySelectorAll("[id='analytic_tag_res']")
        var analytic_tag_list = $(".analytic-tags").select2('data')
        for (var i = 0; i < analytic_tag_list.length; i++) {
            if(analytic_tag_list[i].element[0].selected === true){
                analytic_tag_ids.push(parseInt(analytic_tag_list[i].id))
                if(analytic_tag_text.includes(analytic_tag_list[i].text) === false){
                    analytic_tag_text.push(analytic_tag_list[i].text)
                }
                for (var j = 0; j < analytic_tag_res.length; j++) {
                    analytic_tag_res[j].value = analytic_tag_text
                    analytic_tag_res[j].innerHTML = analytic_tag_res[j].value;
                }
            }
        }
        if (analytic_tag_list.length == 0){
            for (var i = 0; i < analytic_tag_res.length; i++) {
                analytic_tag_res[i].value = ""
                analytic_tag_res[i].innerHTML = "";
            }
        }
        filter_data_selected.analytic_tag_ids = analytic_tag_ids

        if ($(".analytic_group_ids").length) {
            var cat_res = document.querySelectorAll("[id='cat_res']")
            filter_data_selected.analytic_group_ids = $(".analytic_group_ids")[1].value
            for (var i = 0; i < cat_res.length; i++) {
                cat_res[i].value = $(".analytic_group_ids")[1].value
                cat_res[i].innerHTML = $("#category option:selected").text();
                if ($(".analytic_group_ids")[1].value == "") {
                    cat_res[i].innerHTML = "All";
                } if ($(".analytic_group_ids")[1].value == "All") {
                    cat_res[i].innerHTML = "All";
                }
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

        if ($(".book").length) {
            var book_res = document.querySelectorAll("[id='book_res']")
            filter_data_selected.book = $(".book")[1].value
            for (var i = 0; i < book_res.length; i++) {
                book_res[i].value = $(".book")[1].value
                book_res[i].innerHTML = book_res[i].value;
                if ($(".book")[1].value == "") {
                    book_res[i].innerHTML = "commercial";
                }
            }
        }

        var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
        if (currency_item_selected.length) {
            var currency_value = $('ul.o_currency_filter').find('li > a.selected').parent().data('value');
            filter_data_selected.report_currency_id = currency_value;
        }

        var dt;
        var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
        var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
        var comp_detail_res = document.getElementById("comp_detail_res")
        if (list_item_selected.length) {
            var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');

            if (filter_value != "this_month" && filter_value != "today") {
                $(".date-filter").css('display', 'initial');
            }

            if (filter_value == "this_month") {
                dt = new Date();
                dt.setDate(1);
                filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                dt.setMonth(dt.getMonth() + 1);
                dt.setDate(0);
                filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "month";
                comp_detail_res.value = "month";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
            else if (filter_value == "this_quarter") {
                dt = new moment();
                filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "quarter";
                comp_detail_res.value = "quarter";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
            else if (filter_value == "this_financial_year") {
                dt = new Date();
                var year = dt.getFullYear();
                filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "year";
                comp_detail_res.value = "year";
                comp_detail_res.innerHTML = comp_detail_res.value;

            }
            else if (filter_value == "last_month") {
                dt = new Date();
                dt.setMonth(dt.getMonth());
                dt.setDate(1);
                filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                dt.setMonth(dt.getMonth() + 1);
                dt.setDate(0);
                filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "lastmonth";
                comp_detail_res.value = "lastmonth";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
            else if (filter_value == "last_quarter") {
                dt = new moment();
                filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "lastquarter";
                comp_detail_res.value = "lastquarter";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
            else if (filter_value == "last_year") {
                dt = new Date();
                var year = dt.getFullYear();
                filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "lastyear";
                comp_detail_res.value = "lastyear";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
            else if (filter_value == "today") {
                dt = new Date();
                dt.setDate(1);
                filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                dt.setDate(0);
                filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');

                filter_data_selected.comp_detail = "today";
                comp_detail_res.value = "today";
                comp_detail_res.innerHTML = comp_detail_res.value;

            }
            else if (filter_value == "no") {
                dt = new Date();
                filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                if (action_title == 'Balance Sheet'){
                    var comp_detail_res = document.getElementById("comp_detail_res");
                    comp_detail_res.value = "today";
                    comp_detail_res.innerHTML = comp_detail_res.value;
                };

                if (action_title == 'Profit and Loss'){
                    var comp_detail_res = document.getElementById("comp_detail_res");
                    comp_detail_res.value = "month";
                    comp_detail_res.innerHTML = comp_detail_res.value;
                };
            }

            else if (filter_value == "custom_comp") {
                if ($("#date_from").val()) {
                    var dateString = $("#date_from").val();
                    filter_data_selected.date_from = dateString;
                }
                if ($("#date_to").val()) {
                    var dateString = $("#date_to").val();
                    filter_data_selected.date_to = dateString;
                }

                filter_data_selected.comp_detail = "custom_comp";
                comp_detail_res.value = "custom_comp";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
        }

        else if (list_item_selected.length == 0) {
            if ($("#date_from").val()) {
                var dateString = $("#date_from").val();
                filter_data_selected.date_from = dateString;
            }
            if ($("#date_to").val()) {
                var dateString = $("#date_to").val();
                filter_data_selected.date_to = dateString;
            }

            var comp_detail_res = document.getElementById("comp_detail_res")
            filter_data_selected.comp_detail = comp_detail_res.value;
            if (comp_detail_res.value == false) {
                filter_data_selected.comp_detail = "custom";
                comp_detail_res.value = "custom";
                comp_detail_res.innerHTML = comp_detail_res.value;
            }
            
        }


        if ($(".consolidate").length) {
            var consolidate_res = document.querySelectorAll("[id='consolidate_res']")
            filter_data_selected.consolidate = $(".consolidate")[1].value
            for (var i = 0; i < consolidate_res.length; i++) {
                consolidate_res[i].value = $(".consolidate")[1].value
                consolidate_res[i].innerHTML = consolidate_res[i].value;
                if ($(".consolidate")[1].value == "") {
                    consolidate_res[i].innerHTML = "off";
                }
            }
        }

        if ($(".entities_comparison").length) {
            var entities_comparison_res = document.querySelectorAll("[id='entities_comparison_res']")
            filter_data_selected.entities_comparison = $(".entities_comparison")[1].value
            for (var i = 0; i < entities_comparison_res.length; i++) {
                entities_comparison_res[i].value = $(".entities_comparison")[1].value
                entities_comparison_res[i].innerHTML = entities_comparison_res[i].value;
                if ($(".entities_comparison")[1].value == "") {
                    entities_comparison_res[i].innerHTML = "off";
                }
            }
        }

        if ($(".all_account").length) {
            var all_account_res = document.querySelectorAll("[id='all_account_res']")
            filter_data_selected.all_account = $(".all_account")[1].value
            for (var i = 0; i < all_account_res.length; i++) {
                all_account_res[i].value = $(".all_account")[1].value
                all_account_res[i].innerHTML = all_account_res[i].value;
                if ($(".all_account")[1].value == "") {
                    all_account_res[i].innerHTML = "off";
                }
            }
        }

        if ($(".budget").length) {
            var budget_res = document.querySelectorAll("[id='budget_res']")
            filter_data_selected.budget = $(".budget")[1].value
            for (var i = 0; i < budget_res.length; i++) {
                budget_res[i].value = $(".budget")[1].value
                budget_res[i].innerHTML = budget_res[i].value;
                if ($(".budget")[1].value == "") {
                    budget_res[i].innerHTML = "off";
                }
            }
        }

        if ($(".debit_credit").length) {
            var debit_credit_res = document.querySelectorAll("[id='debit_credit_res']")
            filter_data_selected.debit_credit = $(".debit_credit")[1].value
            for (var i = 0; i < debit_credit_res.length; i++) {
                debit_credit_res[i].value = $(".debit_credit")[1].value
                debit_credit_res[i].innerHTML = debit_credit_res[i].value;
                if ($(".debit_credit")[1].value == "") {
                    debit_credit_res[i].innerHTML = "off";
                }
            }
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

        filterdata = filter_data_selected;

        if (filter_data_selected.consolidate != "Off") {
            $(".consolidate-filter").css('display', 'initial');
        }
        if (filter_data_selected.entities_comparison != "Off") {
            $(".entities_comparison-filter").css('display', 'initial');
        }
        if (filter_data_selected.all_account != "Off") {
            $(".all_account-filter").css('display', 'initial');
        }
        if (filter_data_selected.report_currency_id != undefined) {
            $(".currency-filter").css('display', 'initial');
        }
        if (filter_data_selected.journal_ids.length != 0) {
            $(".journals-filter").css('display', 'initial');
        }
        if (filter_data_selected.currency_ids.length != 0) {
            $(".currencies-filter").css('display', 'initial');
        }
        if (filter_data_selected.account_ids.length != 0) {
            $(".accounts-filter").css('display', 'initial');
        }
        if (filter_data_selected.analytic_ids.length != 0) {
            $(".analytic-accounts-filter").css('display', 'initial');
        }
        if (filter_data_selected.analytic_tag_ids.length != 0) {
            $(".analytic-tags-filter").css('display', 'initial');
        }
        if (filter_data_selected.target_move != "Posted") {
            $(".target-move-filter").css('display', 'initial');
        }
        if (filter_data_selected.analytic_group_ids != "") {
            $(".analytic-categories-filter").css('display', 'initial');
        }
        if (filter_data_selected.book != "Commercial") {
            $(".book-filter").css('display', 'initial');
        }
        if (filter_data_selected.comparison != null) {
            $(".comparison-filter").css('display', 'initial');
        }
        if (filter_data_selected.budget != "Off") {
            $(".budget-filter").css('display', 'initial');
        }

        if (filter_data_selected.debit_credit != "Off") {
            $(".debit-credit-filter").css('display', 'initial');
        }

        rpc.query({
            model: 'ctm.dynamic.balance.sheet.report',
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
        var action_title = self._title;
        $(".active-filter, .active-filter a, .clear-filter").css('display', 'none');

        var filter_data_selected = {};

        if (action_title == 'Balance Sheet'){
            $('.filter_date[data-value="today"]').click();
        };
        if (action_title == 'Profit and Loss'){
            $('.filter_date[data-value="this_month"]').click();
        };
        

        var consolidate_res = document.querySelectorAll("[id='consolidate_res']")
        for (var i = 0; i < consolidate_res.length; i++) {
            consolidate_res[i].value = "Off"
            consolidate_res[i].innerHTML = "Off"
        }
        var consolidate_selection = document.getElementById('consolidate');
        for (var i = 0; i < consolidate_selection.options.length; i++) {
            consolidate_selection.options[i].selected = false;
        }
        filter_data_selected.consolidate = "Off"


        var entities_comparison_res = document.querySelectorAll("[id='entities_comparison_res']")
        for (var i = 0; i < entities_comparison_res.length; i++) {
            entities_comparison_res[i].value = "Off"
            entities_comparison_res[i].innerHTML = "Off"
        }
        var entities_comparison_selection = document.getElementById('entities_comparison');
        for (var i = 0; i < entities_comparison_selection.options.length; i++) {
            entities_comparison_selection.options[i].selected = false;
        }
        filter_data_selected.entities_comparison = "Off"

        var all_account_res = document.querySelectorAll("[id='all_account_res']")
        for (var i = 0; i < all_account_res.length; i++) {
            all_account_res[i].value = "Off"
            all_account_res[i].innerHTML = "Off"
        }
        var all_account_selection = document.getElementById('all_account');
        for (var i = 0; i < all_account_selection.options.length; i++) {
            all_account_selection.options[i].selected = false;
        }
        filter_data_selected.all_account = "Off"

        var currency_res = document.querySelectorAll(".currency_caret")
        for (var i = 0; i < currency_res.length; i++) {
            currency_res[i].innerHTML = ""
        }
        var currency_selection = document.querySelectorAll(".filter_currency .dropdown-item")
        for (var i = 0; i < currency_selection.length; i++) {
            if (currency_selection[i].classList.contains("selected")) {
                currency_selection[i].classList.remove("selected")
            }
        }
        filter_data_selected.report_currency_id = false

        var journal_res = document.querySelectorAll("[id='journal_res']")
        for (var i = 0; i < journal_res.length; i++) {
            journal_res[i].value = "All"
            journal_res[i].innerHTML = "All";
        }
        filter_data_selected.journal_ids = []

        var currency_res = document.querySelectorAll("[id='currency_res']")
        for (var i = 0; i < currency_res.length; i++) {
            currency_res[i].value = "All"
            currency_res[i].innerHTML = "All";
        }
        filter_data_selected.currency_ids = []

        var account_res = document.querySelectorAll("[id='acc_res']")
        for (var i = 0; i < account_res.length; i++) {
            account_res[i].value = "All"
            account_res[i].innerHTML = "All";
        }
        filter_data_selected.account_ids = []

        var analytic_res = document.querySelectorAll("[id='analytic_res']")
        for (var i = 0; i < analytic_res.length; i++) {
            analytic_res[i].value = "All"
            analytic_res[i].innerHTML = "All";
        }
        filter_data_selected.analytic_ids = []

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

        var cat_res = document.querySelectorAll("[id='cat_res']")
        for (var i = 0; i < cat_res.length; i++) {
            cat_res[i].value = "All"
            cat_res[i].innerHTML = "All"
        }
        var category_selection = document.getElementById('category');
        for (var i = 0; i < category_selection.options.length; i++) {
            category_selection.options[i].selected = false;
        }
        filter_data_selected.analytic_group_ids = ""

        var book_res = document.querySelectorAll("[id='book_res']")
        for (var i = 0; i < book_res.length; i++) {
            book_res[i].value = "Commercial"
            book_res[i].innerHTML = "Commercial"
        }
        var book_selection = document.getElementById('fiscal_book');
        for (var i = 0; i < book_selection.options.length; i++) {
            book_selection.options[i].selected = false;
        }
        filter_data_selected.book = "Commercial"

        var budget_res = document.querySelectorAll("[id='budget_res']")
        for (var i = 0; i < budget_res.length; i++) {
            budget_res[i].value = "Off"
            budget_res[i].innerHTML = "Off"
        }
        var budget_selection = document.getElementById('budget');
        for (var i = 0; i < budget_selection.options.length; i++) {
            budget_selection.options[i].selected = false;
        }
        filter_data_selected.budget = "Off"

        var debit_credit_res = document.querySelectorAll("[id='debit_credit_res']")
        for (var i = 0; i < debit_credit_res.length; i++) {
            debit_credit_res[i].value = "Off"
            debit_credit_res[i].innerHTML = "Off"
        }
        var debit_credit_selection = document.getElementById('debit_credit');
        for (var i = 0; i < debit_credit_selection.options.length; i++) {
            debit_credit_selection.options[i].selected = false;
        }
        filter_data_selected.debit_credit = "Off"

        filter_data_selected.account_tag_ids = []
        filter_data_selected.analytic_tag_ids = []
        if (action_title == 'Balance Sheet'){
            filter_data_selected.comp_detail = "today"
        };
        if (action_title == 'Profit and Loss'){
            filter_data_selected.comp_detail = "month"
        };
        filter_data_selected.comparison = null;

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

        filter_data_selected.previous = null;

        filterdata = filter_data_selected;
        rpc.query({
            model: 'ctm.dynamic.balance.sheet.report',
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
    core.action_registry.add("c_dfr_n", ProfitAndLoss);
    return ProfitAndLoss;
});
