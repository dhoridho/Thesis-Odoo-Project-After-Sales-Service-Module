odoo.define('equip3_accounting_reports.pettycash_analysis', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var bslinedata = []

    window.click_num = 0;

    var pettycash_analysis = AbstractAction.extend({
        template: 'pettycash_analysis',
        events: {
            'click .plg-line': 'show_drop_down',
            'click .view-account-move': 'view_acc_move',
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click .clear-filter': 'clear_filter',
            'click #apply_filter': 'apply_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click #collapse-button': 'collapse_all',
            'click .o_add_custom_filter_prev': '_onPrevFilter',
            'click .o_add_custom_filter_last': '_onLastFilter',
            
        },

        _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content')) {
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

        collapse_all: function(event) {
            event.preventDefault();
            var self = this;
            var action_title = self._title;
            var report_lines = bslinedata['report_lines'];
            if (!report_lines || !report_lines.length || !report_lines[0] || !report_lines[0]['move_lines']) {
                console.error("Invalid report_lines data");
                return;
            }
        
            var move_lines = report_lines[0]['move_lines'];
        
        
            if ($(event.currentTarget).hasClass('collapse-all')) {
                var acc_data = [];
        
                for (var i = 0; i < report_lines.length; i++) {
                    var move_lines_i = report_lines[i]['move_lines'];
        
                    if (move_lines_i && move_lines_i.length > 0) {
                        acc_data.push(move_lines_i);
                        var target = $(event.target).parents().find('.c' + report_lines[i]['id']);
        
        
                        var account_id = report_lines[i]['id'];
        
                        target.removeClass('collapsed');
                        target.next('tr').addClass('show');
                        target.find('td.' + account_id).css({
                            'visibility': 'hidden',
                        });
        
                        target.next('tr').find('td .pl-table-div').remove();
                        target.next('tr').find('td ul').after(
                            QWeb.render('SubSectionPetty', {
                                account_data: acc_data[i],
                                currency: bslinedata['currency'],
                                currency_position: bslinedata['currency_position'],
                            })
                        );
                    }
                }
            } else {
                for (var i = 0; i < report_lines.length; i++) {
                    var move_lines_i = report_lines[i]['move_lines'];
        
                    if (move_lines_i && move_lines_i.length > 0) {
                        var target = $(event.target).parents().find('.c' + report_lines[i]['id']);
                        var account_id = report_lines[i]['id'];
        
                        target.addClass('collapsed');
                        target.next('tr').removeClass('show');
                        target.find('td.' + account_id).css({
                            'visibility': 'visible',
                        });
                    }
                }
            }
        
            if ($(event.currentTarget).hasClass('collapse-all')) {
                $(event.currentTarget).removeClass('collapse-all');
                $(event.currentTarget).addClass('collapsed-all');
                $(event.currentTarget).text('Collapse');
            } else {
                $(event.currentTarget).removeClass('collapsed-all');
                $(event.currentTarget).addClass('collapse-all');
                $(event.currentTarget).text('Expand');
            }
        },


        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
                   self._rpc({
                        model: 'account.pettycash.analysis',
                        method: 'view_report',
                        args: [
                            [self.wizard_id]
                        ],
                    }).then(function(data) {
                        _.each(data['report_lines'], function(rep_lines) {
                                _.each(rep_lines['move_lines'], function(move_line) {

                                move_line.taxes = self.format_currency(data['currency'],move_line.taxes);
                                move_line.price = self.format_currency(data['currency'],move_line.price);
                                move_line.total = self.format_currency(data['currency'],move_line.total);
                                move_line.balance = self.format_currency(data['currency'],move_line.balance);
                                move_line.virtual_balance = self.format_currency(data['currency'],move_line.virtual_balance); 
                                move_line.virtual_expenses = self.format_currency(data['currency'],move_line.virtual_expenses);    
                                });
                        });


                    for (var i = 0; i < data['report_lines'].length; i++) {
                        if (account_id == data['report_lines'][i]['id'] ){
                            $(event.currentTarget).next('tr').find('td .pl-table-div').remove();
                            $(event.currentTarget).next('tr').find('td ul').after(
                                QWeb.render('SubSectionPetty', {
                                    account_data: data['report_lines'][i]['move_lines'],
                                    currency: data['currency'],
                                    currency_position: data['currency_position'],
                                }))
                            $(event.currentTarget).next('tr').find('td ul li:first a').css({
                                'background-color': '#00ede8',
                                'font-weight': 'bold',
                                });
                             }
                        }
                    });
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

            } else {
                prev_dates.addClass('d-none');
            }
            var last_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-last');
            last_dates.addClass('d-none');
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
            } else {
                last_dates.addClass('d-none');
            }
            var prev_dates = $(ev.target).parents().find('ul.o_filters_menu_comp').find('.o_account_reports_custom-prev');
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
            filter_data_selected.filter_period = 'no'

            rpc.query({
                model: 'account.pettycash.analysis',
                method: 'create',
                args: [filter_data_selected]
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
                    model: 'account.pettycash.analysis',
                    method: 'view_report',
                    args: [[this.wizard_id]],
                }).then(function(datas) {
                    _.each(datas['report_lines'], function(rep_lines) {
                        rep_lines.amount = self.format_currency(datas['currency'],rep_lines.amount);
                        rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                        rep_lines.total_amount = self.format_currency(datas['currency'],rep_lines.total_amount);
                        rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                        rep_lines.total_expenses = self.format_currency(datas['currency'],rep_lines.total_expenses);
                        rep_lines.total_virtual = self.format_currency(datas['currency'],rep_lines.total_virtual);
                        rep_lines.move_lines = _.map(rep_lines.move_lines, function(move_line) {
                            move_line.taxes = self.format_currency(datas['currency'],move_line.taxes);
                            move_line.price = self.format_currency(datas['currency'],move_line.price);
                            move_line.total = self.format_currency(datas['currency'],move_line.total);
                            move_line.balance = self.format_currency(datas['currency'],move_line.balance);
                            move_line.virtual_balance = self.format_currency(datas['currency'],move_line.virtual_balance);
                            move_line.virtual_expenses = self.format_currency(datas['currency'],move_line.virtual_expenses);
                            return move_line;
                        });
                    });
                    for (var i = 0; i < datas['list_periode'].length; i++) {
                        _.each(datas['pettycash_result'][datas['list_periode'][i]], function(rep_lines) {
                            rep_lines.amount = self.format_currency(datas['currency'],rep_lines.amount);
                            rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.total_amount = self.format_currency(datas['currency'],rep_lines.total_amount);
                            rep_lines.total_balance = self.format_currency(datas['currency'],rep_lines.total_balance);
                            rep_lines.total_expenses = self.format_currency(datas['currency'],rep_lines.total_expenses);
                            rep_lines.total_virtual = self.format_currency(datas['currency'],rep_lines.total_virtual);
                            rep_lines.move_lines = _.map(rep_lines.move_lines, function(move_line) {
                                move_line.taxes = self.format_currency(datas['currency'],move_line.taxes);
                                move_line.price = self.format_currency(datas['currency'],move_line.price);
                                move_line.total = self.format_currency(datas['currency'],move_line.total);
                                move_line.balance = self.format_currency(datas['currency'],move_line.balance);
                                move_line.virtual_balance = self.format_currency(datas['currency'],move_line.virtual_balance);
                                move_line.virtual_expenses = self.format_currency(datas['currency'],move_line.virtual_expenses);
                                return move_line;
                            });
                        });
                        datas['list_total_amount'][datas['list_periode'][i]] = self.format_currency(datas['currency'],datas['list_total_amount'][datas['list_periode'][i]]);
                        datas['list_total_balance'][datas['list_periode'][i]] = self.format_currency(datas['currency'],datas['list_total_balance'][datas['list_periode'][i]]);
                        datas['list_total_expenses'][datas['list_periode'][i]] = self.format_currency(datas['currency'],datas['list_total_expenses'][datas['list_periode'][i]]);
                        datas['list_total_virtual'][datas['list_periode'][i]] = self.format_currency(datas['currency'],datas['list_total_virtual'][datas['list_periode'][i]]);
                        
                    }

                    if (initial_render) {
                        self.$('.filter_view_tb').html(QWeb.render('EntPettycashFilterView', {
                            filter_data: datas['filters'],
                        }));
                        $('.filter_date[data-value="month"]').click();
                        self.$el.find('.account').select2({
                            placeholder: ' Accounts...',
                        });
                        self.$el.find('.branchs').select2({
                        placeholder: 'Branch...',
                        });
                        self.$el.find('.top_expenses').select2({
                            placeholder: 'Top Expenses...',
                        });

                        
                    }
                    var child=[];
                    self.$('.table_view_tb').html(QWeb.render('EntPettycashTableView', {
                        report_lines : datas['report_lines'],
                        filter : datas['filters'],
                        currency : datas['currency'],

                        subtotal_taxes : datas['subtotal_taxes'],
                        subtotal_price : datas['subtotal_price'],
                        subtotal_expenses : datas['subtotal_expenses'],

                        total_balance : datas['total_balance'],
                        total_expenses : datas['total_expenses'],
                        total_virtual : datas['total_virtual'],

                        pettycash_result : datas['pettycash_result'],
                        list_periode : datas['list_periode'],

                        list_total_amount : datas['list_total_amount'],
                        list_total_balance : datas['list_total_balance'],
                        list_total_expenses : datas['list_total_expenses'],
                        list_total_virtual : datas['list_total_virtual'],
                        
                    }));
                    bslinedata = datas
                
                    if ($('.collapse-all').length) {
                        $('.collapse-all').click();    
                    } else {
                        $('.collapsed-all').click();
                        $('.collapse-all').click();
                    }
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
            var action_title = self._title
            var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'equip3_accounting_reports.pettycash_analysis',
                    'report_file': 'equip3_accounting_reports.pettycash_analysis',
                    'data': {
                        'report_data': bslinedata,
                        'report_name': 'Petty Cash Analysis'
                    },
                    'context': {
                        'active_model': 'account.pettycash.analysis',
                        'portrait': 1,
                        'petty_cash_pdf_report': true
                    },
                    'display_name': 'Petty Cash Analysis',
                };
                return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'account.pettycash.analysis',
                     'options': JSON.stringify(bslinedata['filters']),
                     'output_format': 'xlsx',
                     'report_data': JSON.stringify(bslinedata['report_lines']),
                     'report_name': 'Petty Cash Analysis',
                     'dfr_data': JSON.stringify(bslinedata),
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

        apply_filter: function(event) {
            $(".active-filter, .clear-filter").css('display', 'block');
            $(".filter_content").css('display', 'none');

            event.preventDefault();
            var self = this;
            self.initial_render = false;
            var filter_data_selected = {};

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

            var branch_ids = [];
            var branch_text = [];
            var span_res = document.querySelectorAll("[id='branch_res']")
            var branch_list = $(".branchs").select2('data')
            for (var i = 0; i < branch_list.length; i++) {
                if(branch_list[i].element[0].selected === true) {
                    branch_ids.push(parseInt(branch_list[i].id))
                    if(branch_text.includes(branch_list[i].text) === false) {
                        branch_text.push(branch_list[i].text)
                    }
                    for (var j = 0; j < span_res.length; j++) {
                        span_res[j].value = branch_text
                        span_res[j].innerHTML = span_res[j].value;
                    }
                }
            }
            if (branch_list.length == 0){
                for (var i = 0; i < span_res.length; i++) {
                    span_res[i].value = ""
                    span_res[i].innerHTML = "All";
                }
            }
            filter_data_selected.branch_ids = branch_ids

            var dt;
            var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            filter_data_selected.date_from = "";
            filter_data_selected.date_to = "";
            if (list_item_selected.length) {
                var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');
                $(".date-filter").css('display', 'initial');                
                filter_data_selected.filter_period = filter_value
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
                if (!filter_data_selected.date_from  || !filter_data_selected.date_from){
                    filter_data_selected.filter_period = 'today'
                }
                else{
                    filter_data_selected.filter_period = 'custom'   
                }
                
            }

            if (currency_item_selected.length) {
                var currency_value = $('ul.o_currency_filter').find('li > a.selected').parent().data('value');
                filter_data_selected.report_currency_id = currency_value;
            }

            if ($(".top_expenses").length) {
                var top_expenses_res = document.querySelectorAll("[id='top_expenses_res']")
                filter_data_selected.top_expenses = $(".top_expenses")[1].value
                for (var i = 0; i < top_expenses_res.length; i++) {
                    top_expenses_res[i].value = $(".top_expenses")[1].value
                    top_expenses_res[i].innerHTML = top_expenses_res[i].value;
                    if ($(".top_expenses")[1].value == "") {
                        top_expenses_res[i].innerHTML = "off";
                    }
                }
            }

            filter_data_selected.period = 0;
            filter_data_selected.years_prev = false;
            if ($("#prev").val()) {
                var prev = $("#prev").val();
                filter_data_selected.period = prev;
                filter_data_selected.years_prev = false;
                document.getElementById("last").value = null;
                document.getElementById("prev").value = null;
            }
            if ($("#last").val()) {
                var last = $("#last").val();
                filter_data_selected.period = last;
                filter_data_selected.years_prev = true;
                document.getElementById("prev").value = null;
                document.getElementById("last").value = null;
            }



            if (filter_data_selected.branch_ids.length != 0) {
                $(".branchs-filter").css('display', 'initial');
            }
            
            if (filter_data_selected.account_ids.length != 0) {
                $(".accounts-filter").css('display', 'initial');
            }

            if (filter_data_selected.top_expenses != "off") {
                $(".top-expenses-filter").css('display', 'initial');
            }

            



            rpc.query({
                model: 'account.pettycash.analysis',
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

            var date_selection = document.querySelectorAll(".filter_date .dropdown-item")
            for (var i = 0; i < date_selection.length; i++) {
                if (date_selection[i].classList.contains("selected")) {
                    date_selection[i].classList.remove("selected")
                }
            }
            $('.date_caret').text("");
    
            var top_expenses_res = document.querySelectorAll("[id='top_expenses_res']")
            for (var i = 0; i < top_expenses_res.length; i++) {
                top_expenses_res[i].value = "Off"
                top_expenses_res[i].innerHTML = "Off"
            }
            var top_expenses_selection = document.getElementById('top_expenses');
            for (var i = 0; i < top_expenses_selection.options.length; i++) {
                top_expenses_selection.options[i].selected = false;
            }
            filter_data_selected.top_expenses = "Off"

    
            var account_res = document.querySelectorAll("[id='acc_res']")
            for (var i = 0; i < account_res.length; i++) {
                account_res[i].value = "All"
                account_res[i].innerHTML = "All";
            }
            filter_data_selected.account_ids = []

            var branch_res = document.querySelectorAll("[id='branch_res']")
            for (var i = 0; i < branch_res.length; i++) {
                branch_res[i].value = "All"
                branch_res[i].innerHTML = "All";
            }
            filter_data_selected.branch_ids = []

            filter_data_selected.filter_period = 'month'
            filter_data_selected.period = 0;
    
            var search_choice = document.querySelectorAll(".select2-search-choice")
            for (var i = 0; i < search_choice.length; i++) {
                search_choice[i].remove()
            }
            var chosen = document.querySelectorAll(".select2-chosen")
            for (var i = 0; i < chosen.length; i++) {
                chosen[i].value = ""
                chosen[i].innerHTML = ""
            }
    
            rpc.query({
                model: 'account.pettycash.analysis',
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
    core.action_registry.add('ent_p', pettycash_analysis);
    return pettycash_analysis;
});







