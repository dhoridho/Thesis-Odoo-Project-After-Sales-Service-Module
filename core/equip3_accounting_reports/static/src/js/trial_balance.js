odoo.define('equip3_accounting_reports.trial', function (require) {
    'use strict';
    var TrialBalance = require('dynamic_cash_flow_statements.trial');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var rpc = require('web.rpc');
    var filterdata = {};
    var sessionStorage = window.sessionStorage;

    window.click_num = 0;
    TrialBalance.include({
        events: _.extend({}, TrialBalance.prototype.events, {
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click': '_onAnyWhereClick',
            'click .btn-sort': 'onClickSort',
        }),

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
        },
        load_data: function (initial_render = true, sort=false, sort_type=false) {
            var self = this;
                self.$(".categ").empty();
                $('div.o_action_manager').css('overflow-y', 'auto');
                try{
                    var self = this;
                    self._rpc({
                        model: 'account.trial.balance',
                        method: 'view_report',
                        args: [[this.wizard_id]],
                        kwargs: {sort: sort, sort_type: sort_type},
                    }).then(function(datas) {
                        // sessionStorage.setItem('data_tb', JSON.stringify(datas));
                        var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                        sessionStorage.setItem('data_tb', compressedData);
                        var opening_debit_total = 0
                        var opening_credit_total = 0
                        var ending_balance_debit_total = 0
                        var ending_balance_credit_total = 0
                        _.each(datas['report_lines'], function(rep_lines) {
                            rep_lines['opening_balance'] = rep_lines.opening_debit - rep_lines.opening_credit;
                            if (rep_lines['opening_balance'] > 0){
                                opening_debit_total += rep_lines.opening_balance
                                rep_lines.opening_debit = rep_lines.opening_balance;
                                rep_lines.opening_credit = 0;
                            }
                            else if (rep_lines['opening_balance'] < 0){
                                opening_credit_total += (-rep_lines.opening_balance)
                                rep_lines.opening_debit = 0;
                                rep_lines.opening_credit = -rep_lines.opening_balance;
                            }
                            else{
                                rep_lines.opening_debit = 0;
                                rep_lines.opening_credit = 0;
                            }

                            rep_lines['ending_balance'] = rep_lines.ending_debit - rep_lines.ending_credit;
                            if (rep_lines['ending_balance'] > 0){
                                ending_balance_debit_total += rep_lines.ending_balance
                                rep_lines.ending_balance_debit = rep_lines.ending_balance;
                                rep_lines.ending_balance_credit = 0;
                            }
                            else if (rep_lines['ending_balance'] < 0){
                                ending_balance_credit_total += (-rep_lines.ending_balance)
                                rep_lines.ending_balance_debit = 0;
                                rep_lines.ending_balance_credit = -rep_lines.ending_balance;
                            }
                            else{
                                rep_lines.ending_balance_debit = 0
                                rep_lines.ending_balance_credit = 0
                            }
                            
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                            rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                            rep_lines.ending_debit = self.format_currency(datas['currency'],rep_lines.ending_debit);
                            rep_lines.ending_credit = self.format_currency(datas['currency'],rep_lines.ending_credit);
                            rep_lines.ending_balance = self.format_currency(datas['currency'],rep_lines.ending_balance);
                            rep_lines.ending_balance_debit = self.format_currency(datas['currency'],rep_lines.ending_balance_debit);
                            rep_lines.ending_balance_credit = self.format_currency(datas['currency'],rep_lines.ending_balance_credit);
                            rep_lines.opening_debit = self.format_currency(datas['currency'],rep_lines.opening_debit);
                            rep_lines.opening_credit = self.format_currency(datas['currency'],rep_lines.opening_credit);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);

                        });
                        datas['opening_debit_total'] = opening_debit_total
                        datas['opening_credit_total'] = opening_credit_total
                        datas['ending_balance_debit_total'] = ending_balance_debit_total
                        datas['ending_balance_credit_total'] = ending_balance_credit_total

                        if (initial_render) {
                                self.$('.filter_view_tb').html(QWeb.render('TrialFilterView', {
                                    filter_data: datas['filters'],
                                }));
                                self.$el.find('.journals').select2({
                                    placeholder: 'Select Journals...',
                                });
                                self.$el.find('.target_move').select2({
                                    placeholder: 'Target Move...',
                                });
                                self.$el.find('.consolidate').select2({
                                    placeholder: 'consolidation...',
                                });
                                self.$el.find('.all_account').select2({
                                    placeholder: 'All Account...',
                                });
                        }
                        var child=[];
                        var renderPromise = self.$('.table_view_tb').html(QWeb.render('TrialTable', {
                            report_lines : datas['report_lines'],
                            filter : datas['filters'],
                            currency : datas['currency'],
                            credit_total : self.format_currency(datas['currency'],datas['credit_total']),
                            debit_total : self.format_currency(datas['currency'],datas['debit_total']),
                            opening_credit_total : self.format_currency(datas['currency'],datas['opening_credit_total']),
                            opening_debit_total : self.format_currency(datas['currency'],datas['opening_debit_total']),
                            ending_credit_total : self.format_currency(datas['currency'],datas['ending_credit_total']),
                            ending_debit_total : self.format_currency(datas['currency'],datas['ending_debit_total']),
                            ending_balance_total : self.format_currency(datas['currency'],datas['ending_balance_total']),
                            ending_balance_debit_total : self.format_currency(datas['currency'],datas['ending_balance_debit_total']),
                            ending_balance_credit_total : self.format_currency(datas['currency'],datas['ending_balance_credit_total']),
                            all_account : datas.filters.all_account,
                        }));

                        renderPromise.promise().done(function () {
                            if (sort) {
                                if (sort_type == 'asc') {
                                    $(`[data-sort=${sort}]`).removeClass('fa-sort fa-sort-up').addClass('fa-sort-down').css('color','black');
                                } else if (sort_type == 'desc') {
                                    $(`[data-sort=${sort}]`).removeClass('fa-sort-down').addClass('fa-sort-up').css('color','black');
                                }
                            }
                        });
                    });
                }
                catch (el) {
                    window.location.href
                }
            },
        apply_filter: function(event) {
            $(".active-filter, .clear-filter").css('display', 'block');
            $(".filter_content").css('display', 'none');

            event.preventDefault();
            var self = this;
            self.initial_render = false;

            var filter_data_selected = {};
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
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "last_quarter") {
                    dt = new Date();
                    dt.setMonth((moment(dt).quarter() - 1) * 3);
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    dt.setDate(1);
                    dt.setMonth(dt.getMonth() - 2);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "last_year") {
                    dt = new Date();
                    var year = dt.getFullYear() - 1;
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
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

            filterdata = filter_data_selected;

            if (filter_data_selected.journal_ids.length != 0) {
                $(".journals-filter").css('display', 'initial');
            }
            if (filter_data_selected.target_move != "Posted") {
                $(".target-move-filter").css('display', 'initial');
            }
            if (filter_data_selected.consolidate != "off") {
                $(".consolidate-filter").css('display', 'initial');
            }

            if (filter_data_selected.all_account != "Off") {
                $(".all_account-filter").css('display', 'initial');
            }
            
            rpc.query({
                model: 'account.trial.balance',
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

            var date_selection = document.querySelectorAll(".filter_date .dropdown-item")
            for (var i = 0; i < date_selection.length; i++) {
                if (date_selection[i].classList.contains("selected")) {
                    date_selection[i].classList.remove("selected")
                }
            }
            $('.date_caret').text("");

            var journal_res = document.querySelectorAll("[id='journal_res']")
            for (var i = 0; i < journal_res.length; i++) {
                journal_res[i].value = "All"
                journal_res[i].innerHTML = "All";
            }
            filter_data_selected.journal_ids = []

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

            var consolidate_res = document.querySelectorAll("[id='consolidate_res']")
            for (var i = 0; i < consolidate_res.length; i++) {
                consolidate_res[i].value = "off"
                consolidate_res[i].innerHTML = "off"
            }
            var consolidate_selection = document.getElementById('consolidate');
            for (var i = 0; i < consolidate_selection.options.length; i++) {
                consolidate_selection.options[i].selected = false;
            }
            filter_data_selected.consolidate = "off"

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
            filter_data_selected.date_from = "";

            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);
            filter_data_selected.date_to = "";

            filterdata = filter_data_selected;

            rpc.query({
                model: 'account.trial.balance',
                method: 'write',
                args: [
                    self.wizard_id, filter_data_selected
                ],
            }).then(function(res) {
            self.initial_render = true;
                self.load_data(self.initial_render);
            });
        },

        show_gl: function(e) {
            var self = this;
            var account_id = $(e.target).attr('data-account-id');
            // var obj = JSON.parse(sessionStorage.getItem('data_tb'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tb')));
            var options = {
                account_ids: [account_id],
            }
            var action = {
                type: 'ir.actions.client',
                name: 'GL View',
                tag: 'g_l',
                target: 'new',
                domain: [['account_ids','=', account_id], 
                         ['trial_balance'], 
                         [{'account_ids' : account_id,
                           'view_report' : 'trial_balance',
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
            // var obj = JSON.parse(sessionStorage.getItem('data_tb'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tb')));
            var opening_debit_total = 0
            var opening_credit_total = 0
            var ending_balance_debit_total = 0
            var ending_balance_credit_total = 0
            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['opening_balance'] = rep_lines.opening_debit - rep_lines.opening_credit;
                if (rep_lines['opening_balance'] > 0){
                    rep_lines.opening_debit = rep_lines.opening_balance;
                    rep_lines.opening_credit = 0;
                    opening_debit_total += rep_lines.opening_balance
                }
                else if (rep_lines['opening_balance'] < 0){
                    rep_lines.opening_debit = 0;
                    rep_lines.opening_credit = -rep_lines.opening_balance;
                    opening_credit_total += (-rep_lines.opening_balance)
                }
                else{
                    rep_lines.opening_debit = 0;
                    rep_lines.opening_credit = 0;   
                }

                rep_lines['ending_balance'] = rep_lines.ending_balance_debit - rep_lines.ending_balance_credit;
                if (rep_lines['ending_balance'] > 0){
                    rep_lines.ending_balance_debit = rep_lines.ending_balance;
                    rep_lines.ending_balance_credit = 0;
                    ending_balance_debit_total += rep_lines.ending_balance
                }
                else if (rep_lines['ending_balance'] < 0){
                    rep_lines.ending_balance_debit = 0;
                    rep_lines.ending_balance_credit = -rep_lines.ending_balance;
                    ending_balance_credit_total += (-rep_lines.ending_balance)
                }
                else{
                    rep_lines.ending_balance_debit = 0;
                    rep_lines.ending_balance_credit = 0;   
                }

            });
            obj['opening_debit_total'] = opening_debit_total
            obj['opening_credit_total'] = opening_credit_total
            obj['ending_balance_debit_total'] = ending_balance_debit_total
            obj['ending_balance_credit_total'] = ending_balance_credit_total
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'dynamic_accounts_report.trial_balance',
                'report_file': 'dynamic_accounts_report.trial_balance',
                'data': {
                    'report_data': obj
                },
                'context': {
                    'active_model': 'account.trial.balance',
                    'landscape': 1,
                    'trial_pdf_report': true
                },
                'display_name': 'Trial Balance',
            };
            return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            // var obj = JSON.parse(sessionStorage.getItem('data_tb'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tb')));
            var opening_debit_total = 0
            var opening_credit_total = 0
            var ending_balance_debit_total = 0
            var ending_balance_credit_total = 0
            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['opening_balance'] = rep_lines.opening_debit - rep_lines.opening_credit;
                if (rep_lines['opening_balance'] > 0){
                    rep_lines.opening_debit = rep_lines.opening_balance;
                    rep_lines.opening_credit = 0;
                    opening_debit_total += rep_lines.opening_balance
                }
                else if (rep_lines['opening_balance'] < 0){
                    rep_lines.opening_debit = 0;
                    rep_lines.opening_credit = -rep_lines.opening_balance;
                    opening_credit_total += (-rep_lines.opening_balance)
                }
                else{
                    rep_lines.opening_debit = 0;
                    rep_lines.opening_credit = 0;   
                }

                rep_lines['ending_balance'] = rep_lines.ending_balance_debit - rep_lines.ending_balance_credit;
                if (rep_lines['ending_balance'] > 0){
                    rep_lines.ending_balance_debit = rep_lines.ending_balance;
                    rep_lines.ending_balance_credit = 0;
                    ending_balance_debit_total += rep_lines.ending_balance
                }
                else if (rep_lines['ending_balance'] < 0){
                    rep_lines.ending_balance_debit = 0;
                    rep_lines.ending_balance_credit = -rep_lines.ending_balance;
                    ending_balance_credit_total += (-rep_lines.ending_balance)
                }
                else{
                    rep_lines.ending_balance_debit = 0;
                    rep_lines.ending_balance_credit = 0;   
                }
            });
            obj['opening_debit_total'] = opening_debit_total
            obj['opening_credit_total'] = opening_credit_total
            obj['ending_balance_debit_total'] = ending_balance_debit_total
            obj['ending_balance_credit_total'] = ending_balance_credit_total
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'account.trial.balance',
                     'options': JSON.stringify(obj['filters']),
                     'output_format': 'xlsx',
                     'report_data': JSON.stringify(obj['report_lines']),
                     'report_name': 'Trial Balance',
                     'dfr_data': JSON.stringify(obj),
                },
            };
            return self.do_action(action);
        },
    });
    core.action_registry.add("t_b", TrialBalance);
    return TrialBalance;
});