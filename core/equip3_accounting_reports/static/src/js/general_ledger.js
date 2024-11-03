odoo.define('equip3_accounting_reports.general_ledger', function (require) {
    'use strict';

    var GeneralLedger = require('dynamic_cash_flow_statements.general_ledger');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;
    var data_gl = [];
    var sessionStorage = window.sessionStorage;

    window.click_num = 0;

    GeneralLedger.include({
    	events: _.extend({}, GeneralLedger.prototype.events, {
    		'click .filter_date_gl': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click #collapse-button': 'collapse_all',
            'click .btn-sort': 'onClickSort',
            'click .btn-sort-line': 'onClickSortLine',
            'click .gl-line': 'show_drop_down',
        }),

        init: function(parent, action) {
        this._super(parent, action);
                this.currency=action.currency;
                this.report_lines = action.report_lines;
                this.custom_data = action.custom_data || null;
                this.wizard_id = action.context.wizard | null;
            },


          start: function() {
            var self = this;
            self.initial_render = true;
            if (self.searchModel.config.domain.length != 0) {
                var filter_data_selected = {};
                filter_data_selected.account_ids = [self.searchModel.config.domain[0][2]];                
                if (self.searchModel.config.domain[1] == 'trial_balance') {
                    var filters = self.searchModel.config.domain[2][0].filters
                    filter_data_selected.account_ids = [self.searchModel.config.domain[2][0].account_ids];
                    filter_data_selected.date_from = filters.date_from;
                    filter_data_selected.date_to = filters.date_to;
                }
                
                if (self.searchModel.config.domain[1] == 'Profit and Loss') {
                    var filters = self.searchModel.config.domain[2][0].filters
                    filter_data_selected.account_ids = [self.searchModel.config.domain[2][0].account_ids];
                    filter_data_selected.date_from = filters.date_from;
                    filter_data_selected.date_to = filters.date_to;
                }

                if (self.searchModel.config.domain[1] == 'Balance Sheet') {
                    var filters = self.searchModel.config.domain[2][0].filters
                    filter_data_selected.account_ids = [self.searchModel.config.domain[2][0].account_ids];
                    var dt = new Date();
                    var year = dt.getFullYear() - 100;                        
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_to = filters.date_to;
                }

                if (self.searchModel.config.domain[1] == 'cash_flow') {
                    var filters = self.searchModel.config.domain[2][0].filters
                    filter_data_selected.account_ids = [self.searchModel.config.domain[2][0].account_ids];
                    filter_data_selected.date_from = filters.date_from;
                    filter_data_selected.date_to = filters.date_to;
                }

                rpc.query({
                    model: 'account.general.ledger',
                    method: 'create',
                    args: [filter_data_selected]
                }).then(function(t_res) {
                    self.wizard_id = t_res;
                    self.load_data(self.initial_render);
                })
            }
            else
            {
            rpc.query({
                    model: 'account.general.ledger',
                    method: 'create',
                    args: [{

                    }]
                }).then(function(t_res) {
                    self.wizard_id = t_res;
                    self.load_data(self.initial_render);
                })
            }
        },


        _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content') && !ev.target.className.includes('dropdown-item')) {
                if ($('.filter_content').css('display') != 'none') {
                    $(".filter_content").css('display', 'none');
                }
            }  
        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            var action_title = self._title
            // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['balance_amount'] = rep_lines.balance
                if (rep_lines['balance_amount'] > 0){
                    rep_lines.debit = rep_lines.balance;
                    rep_lines.credit = 0
                }
                else if (rep_lines['balance_amount'] < 0){
                    rep_lines.debit = 0
                    rep_lines.credit = -rep_lines.balance
                }
                else{
                    rep_lines.debit = 0
                    rep_lines.credit = 0
                }
                _.each(rep_lines['move_lines'], function(move_line) {
                    move_line['balance_amount'] = move_line.balance
                    if (move_line['balance_amount'] > 0){
                        move_line.debit = move_line.balance
                        move_line.credit = 0
                    }
                    else if (move_line['balance_amount'] < 0){
                        move_line.debit = 0
                        move_line.credit = -move_line.balance
                    }
                    else{
                        move_line.debit = 0
                        move_line.credit = 0
                    }
                });
            });
            var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'dynamic_accounts_report.general_ledger',
                    'report_file': 'dynamic_accounts_report.general_ledger',
                    'data': {
                        'report_data': obj
                    },
                    'context': {
                        'active_model': 'account.general.ledger',
                        'landscape': 1,
                        'trial_pdf_report': true
                    },
                    'display_name': action_title,
                };
                return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['balance_amount'] = rep_lines.balance
                if (rep_lines['balance_amount'] > 0){
                    rep_lines.debit = rep_lines.balance;
                    rep_lines.credit = 0
                }
                else if (rep_lines['balance_amount'] < 0){
                    rep_lines.debit = 0
                    rep_lines.credit = -rep_lines.balance
                }
                else{
                    rep_lines.debit = 0
                    rep_lines.credit = 0
                }
                _.each(rep_lines['move_lines'], function(move_line) {
                    move_line['balance_amount'] = move_line.balance
                    if (move_line['balance_amount'] > 0){
                        move_line.debit = move_line.balance
                        move_line.credit = 0
                    }
                    else if (move_line['balance_amount'] < 0){
                        move_line.debit = 0
                        move_line.credit = -move_line.balance
                    }
                    else{
                        move_line.debit = 0
                        move_line.credit = 0
                    }
                });
            });
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'account.general.ledger',
                     'options': JSON.stringify(obj['filters']),
                     'output_format': 'xlsx',
                     'report_data': JSON.stringify(obj['report_lines']),
                     'report_name': action_title,
                     'dfr_data': JSON.stringify(obj),
                },
            };
            return self.do_action(action);
        },

        collapse_all: function(event) {
            event.preventDefault();
            var self = this;
            var action_title = self._title;
            $('.table_view_tb .table_main_view > table > tbody > tr.gl-line[data-account-id]').each(function(ev){
                let $row = $(this);
                if ($(event.currentTarget).hasClass('collapse-all')){
                    var account_id = $row.data('account-id');
                    var td = $row.next('tr').find('td');
                    if (td.length == 1) {
                        self._rpc({
                            model: 'account.general.ledger',
                            method: 'view_report',
                            args: [[self.wizard_id], action_title, account_id],
                        }).then(function(data) {
                            if (!(data.hasOwnProperty('currency'))) {
                                data['currency'] = []
                            }
                            // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
                            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
                            for (var i = 0; i < data['report_lines'].length; i++) {
                                if (account_id == data['report_lines'][i]['id'] ){
                                    for (var j = 0; j < obj['report_lines'].length; j++) {
                                        if (obj['report_lines'][j]['id'] == data['report_lines'][i]['id'] ){
                                            obj['report_lines'][j]['move_lines'] = data['report_lines'][i]['move_lines'];
                                        }
                                    }
                                }
                            }
                            // sessionStorage.setItem('data_gl', JSON.stringify(obj));
                            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
                            sessionStorage.setItem('data_gl', compressedData);
                            _.each(data['report_lines'], function(rep_lines) {
                                rep_lines['balance_amount'] = rep_lines.balance
                                if (rep_lines['balance_amount'] > 0){
                                    rep_lines.debit = self.format_currency(data['currency'],rep_lines.balance);
                                    rep_lines.credit = self.format_currency(data['currency'],0);
                                }
                                else if (rep_lines['balance_amount'] < 0){
                                    rep_lines.debit = self.format_currency(data['currency'],0);
                                    rep_lines.credit = self.format_currency(data['currency'],-rep_lines.balance);
                                }
                                else{
                                    rep_lines.debit = self.format_currency(data['currency'],0);
                                    rep_lines.credit = self.format_currency(data['currency'],0);   
                                }
                                rep_lines.balance = self.format_currency(data['currency'],rep_lines.balance);
                                _.each(rep_lines['move_lines'], function(move_line) {
                                    move_line['balance_amount'] = move_line.balance
                                    if (move_line['balance_amount'] > 0){
                                        move_line.debit = self.format_currency(data['currency'],move_line.balance);
                                        move_line.credit = self.format_currency(data['currency'],0);
                                    }
                                    else if (move_line['balance_amount'] < 0){
                                        move_line.debit = self.format_currency(data['currency'],0);
                                        move_line.credit = self.format_currency(data['currency'],-move_line.balance);
                                    }
                                    else{
                                        move_line.debit = self.format_currency(data['currency'],0);
                                        move_line.credit = self.format_currency(data['currency'],0);   
                                    }
                                    move_line.amount_currency = self.format_currency(data['currency'],move_line.amount_currency);
                                    move_line.balance = self.format_currency(data['currency'],move_line.balance);
                                    if (move_line.partner_name == null) {
                                        move_line.partner_name = ''
                                    }
                                });
                            });
                            for (var i = 0; i < data['report_lines'].length; i++) {
                                if (account_id == data['report_lines'][i]['id'] ){
                                    $row.next('tr').find('td .gl-table-div').remove();
                                    $row.next('tr').find('td ul').after(
                                        QWeb.render('SubSection', {
                                            account_data : data['report_lines'][i]['move_lines'],
                                            currency : data.currency,
                                            currency_symbol : data.currency[0],
                                            currency_position : data.currency[1],                                            
                                        }))
                                    $row.next('tr').find('td ul li:first a').css({
                                        'background-color': '#00ede8',
                                        'font-weight': 'bold',
                                    });
                                    $row.removeClass('collapsed');
                                    $row.next('tr').addClass('show');
                                }
                            }
                        });
                    }
                } else {
                    $row.next('tr').find('td .gl-table-div').remove();
                    $row.addClass('collapsed');
                    $row.next('tr').removeClass('show');
                }
            });
            // var obj2 = JSON.parse(sessionStorage.getItem('data_gl'));
            var obj2 = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
            if ($(event.currentTarget).hasClass('collapse-all')){
                $(event.currentTarget).removeClass('collapse-all');
                $(event.currentTarget).addClass('collapsed-all');
                $(event.currentTarget).text('Collapse');
                (obj2['filters'])['expand'] = true
                
            }else{
                $(event.currentTarget).removeClass('collapsed-all');
                $(event.currentTarget).addClass('collapse-all');
                $(event.currentTarget).text('Expand');
                (obj2['filters'])['expand'] = false
                this.clear_lines();
            }
            // sessionStorage.setItem('data_gl', JSON.stringify(obj2));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj2));
            sessionStorage.setItem('data_gl', compressedData);
        },

        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            var action_title = self._title
            self._rpc({
                model: 'account.general.ledger',
                method: 'view_report',
                context: {'custom_data': self.custom_data || null},
                args: [
                        [self.wizard_id], action_title, account_id
                      ],
            }).then(function(data) {
                // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
                var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
                if (!(data.hasOwnProperty('currency'))) {
                    data['currency'] = []
                }
                for (var i = 0; i < data['report_lines'].length; i++) {
                    if (account_id == data['report_lines'][i]['id'] ){
                        for (var j = 0; j < obj['report_lines'].length; j++) {
                            if (obj['report_lines'][j]['id'] == data['report_lines'][i]['id'] ){
                                if ($(event.currentTarget).hasClass('collapsed')){
                                    obj['report_lines'][j]['move_lines'] = [];
                                }
                                else {
                                    obj['report_lines'][j]['move_lines'] = data['report_lines'][i]['move_lines'];
                                }
                            }
                        }
                    }
                }
                // sessionStorage.setItem('data_gl', JSON.stringify(obj));
                var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
                sessionStorage.setItem('data_gl', compressedData);
                _.each(data['report_lines'], function(rep_lines) {
                    rep_lines['balance_amount'] = rep_lines.balance
                    if (rep_lines['balance_amount'] > 0){
                        rep_lines.debit = self.format_currency(data['currency'],rep_lines.balance);
                        rep_lines.credit = self.format_currency(data['currency'],0);
                    }
                    else if (rep_lines['balance_amount'] < 0){
                        rep_lines.debit = self.format_currency(data['currency'],0);
                        rep_lines.credit = self.format_currency(data['currency'],-rep_lines.balance);
                    }
                    else{
                        rep_lines.debit = self.format_currency(data['currency'],0);
                        rep_lines.credit = self.format_currency(data['currency'],0);   
                    }
                    rep_lines.balance = self.format_currency(data['currency'],rep_lines.balance);
                    _.each(rep_lines['move_lines'], function(move_line) {
                        move_line['balance_amount'] = move_line.balance
                        if (move_line['balance_amount'] > 0){
                            move_line.debit = self.format_currency(data['currency'],move_line.balance);
                            move_line.credit = self.format_currency(data['currency'],0);
                        }
                        else if (move_line['balance_amount'] < 0){
                            move_line.debit = self.format_currency(data['currency'],0);
                            move_line.credit = self.format_currency(data['currency'],-move_line.balance);
                        }
                        else{
                            move_line.debit = self.format_currency(data['currency'],0);
                            move_line.credit = self.format_currency(data['currency'],0);   
                        }
                        move_line.amount_currency = self.format_currency(data['currency'],move_line.amount_currency);
                        move_line.balance = self.format_currency(data['currency'],move_line.balance);
                        if (move_line.partner_name == null) {
                            move_line.partner_name = ''
                        }
                    });
                });
                for (var i = 0; i < data['report_lines'].length; i++) {
                    if (account_id == data['report_lines'][i]['id'] ){
                        if (td.length == 1) {
                            $(event.currentTarget).next('tr').find('td .gl-table-div').remove();
                            $(event.currentTarget).next('tr').find('td ul').after(
                                QWeb.render('SubSection', {
                                    account_data : data['report_lines'][i]['move_lines'],
                                    currency : data.currency,
                                    currency_symbol : data.currency[0],
                                    currency_position : data.currency[1],
                                })) 
                            $(event.currentTarget).next('tr').find('td ul li:first a').css({
                                'background-color': '#00ede8',
                                'font-weight': 'bold',
                            });
                        }
                    }
                }
            });
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
            var self = this
            var sort = ev.currentTarget.dataset.sort
            var sort_type = false

            if ($(ev.currentTarget).hasClass('fa-sort') || $(ev.currentTarget).hasClass('fa-sort-up')) {
                sort_type = 'asc'
            } else {
                sort_type = 'desc'
            }

            // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
            obj['report_lines'].sort(function(a, b) {
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

            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['balance_amount'] = rep_lines.balance
                if (rep_lines['balance_amount'] > 0){
                    rep_lines.debit = self.format_currency(obj['currency'],rep_lines.balance);
                    rep_lines.credit = self.format_currency(obj['currency'],0);
                }
                else if (rep_lines['balance_amount'] < 0){
                    rep_lines.debit = self.format_currency(obj['currency'],0);
                    rep_lines.credit = self.format_currency(obj['currency'],-rep_lines.balance);
                }
                else{
                    rep_lines.debit = self.format_currency(obj['currency'],0);
                    rep_lines.credit = self.format_currency(obj['currency'],0);   
                }
                rep_lines.balance = self.format_currency(obj['currency'],rep_lines.balance);
                _.each(rep_lines['move_lines'], function(move_line) {
                    move_line['balance_amount'] = move_line.balance
                    if (move_line['balance_amount'] > 0){
                        move_line.debit = self.format_currency(obj['currency'],move_line.balance);
                        move_line.credit = self.format_currency(obj['currency'],0);
                    }
                    else if (move_line['balance_amount'] < 0){
                        move_line.debit = self.format_currency(obj['currency'],0);
                        move_line.credit = self.format_currency(obj['currency'],-move_line.balance);
                    }
                    else{
                        move_line.debit = self.format_currency(obj['currency'],0);
                        move_line.credit = self.format_currency(obj['currency'],0);   
                    }
                    move_line.amount_currency = self.format_currency(obj['currency'],move_line.amount_currency);
                    move_line.balance = self.format_currency(obj['currency'],move_line.balance);
                });
            });

            if (!(obj.hasOwnProperty('currency'))) {
                obj['currency'] = []
            }

            var renderPromise = self.$('.table_view_tb').html(QWeb.render('GLTable', {
                report_lines : obj['report_lines'],
                filter : obj['filters'],
                currency : obj['currency'],
                credit_total : obj['credit_total'],
                debit_total : obj['debit_total'],
                debit_balance : obj['debit_balance'],
                all_account : obj.filters.all_account,
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

            self.clear_lines();
        },

        onClickSortLine: function(ev) {
            ev.preventDefault();
            var sort = ev.currentTarget.dataset.sort;
            var sort_type = false;

            if ($(ev.currentTarget).hasClass('fa-sort') || $(ev.currentTarget).hasClass('fa-sort-up')) {
                sort_type = 'asc'
            } else {
                sort_type = 'desc'
            }
            
            // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
            var gl_line = $(ev.currentTarget).closest('tr.collapse').siblings('.gl-line');

            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['move_lines'].sort(function(a, b) {
                    var strSortArray = ['partner_name', 'lname']
                    if (sort_type == 'asc') {
                        if (strSortArray.includes(sort)) {
                            return (a[sort].toLowerCase() > b[sort].toLowerCase()) ? 1 : ((a[sort].toLowerCase() < b[sort].toLowerCase()) ? -1 : 0);
                        } else {
                            return (a[sort] > b[sort]) ? 1 : ((a[sort] < b[sort]) ? -1 : 0);
                        }
                    } else {
                        if (strSortArray.includes(sort)) {
                            return (b[sort].toLowerCase() > a[sort].toLowerCase()) ? 1 : ((b[sort].toLowerCase() < a[sort].toLowerCase()) ? -1 : 0);
                        } else {
                            return (b[sort] > a[sort]) ? 1 : ((b[sort] < a[sort]) ? -1 : 0);
                        }
                    }
                });
            });

            _.each(gl_line, function(line) {
                _.each(obj['report_lines'], function(rep_lines) {
                    if ($(line).data('account-id') == rep_lines['id']) {
                        $(line).next('tr').find('td .gl-table-div').remove();
                        $(line).next('tr').find('td ul').after(
                            QWeb.render('SubSection', {
                                account_data : rep_lines['move_lines'],
                                currency : data.currency,
                                currency_symbol : obj.currency[0],
                                currency_position : obj.currency[1],
                            })) 
                        $(line).next('tr').find('td ul li:first a').css({
                            'background-color': '#00ede8',
                            'font-weight': 'bold',
                        });
                    }
                });
            });

            if (sort_type == 'asc') {
                $(`.btn-sort-line[data-sort=${sort}]`).removeClass('fa-sort fa-sort-up').addClass('fa-sort-down').css('color','black');
            } else if (sort_type == 'desc') {
                $(`.btn-sort-line[data-sort=${sort}]`).removeClass('fa-sort-down').addClass('fa-sort-up').css('color','black');
            }

            // sessionStorage.setItem('data_gl', JSON.stringify(obj));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_gl', compressedData);
        },

        _onFilterDate: function(ev) {
            ev.preventDefault();
            $(ev.target).parents().find('ul.o_date_filter_gl').find('li > a.selected').removeClass('selected');
            if (!$('.o_account_reports_custom_gl-dates').hasClass('d-none')) {
                $('.o_account_reports_custom_gl-dates').addClass('d-none');
            }
            if ($(ev.target).is('a')) {
                $(ev.target).addClass('selected');
            }
            else {
                $(ev.target).find('a').addClass('selected');
            }
            var title = $(ev.target).parents().find('ul.o_date_filter_gl').find('li > a.selected').parent().attr('title');
            $('.date_caret_gl').text(title);
        },

    	_onCustomFilter: function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            $(ev.target).parents().find('ul.o_filters_menu_gl').find('li > a.selected').removeClass('selected');
            var custom_dates = $(ev.target).parents().find('ul.o_filters_menu_gl').find('.o_account_reports_custom_gl-dates');
            if (custom_dates.hasClass('d-none')) {
                custom_dates.removeClass('d-none');
                $('.date_caret_gl').text('Custom');
            } else {
                custom_dates.addClass('d-none');
            }
            
        },

        load_data: function (initial_render = true) {
            var self = this;
            self.$(".categ").empty();
            $('div.o_action_manager').css('overflow-y', 'auto');
            try{
                var self = this;
                var action_title = self._title
                self._rpc({
                    model: 'account.general.ledger',
                    method: 'view_report',
                    context: {'custom_data': self.custom_data || null},
                    args: [[this.wizard_id], action_title],
                }).then(function(datas) {
                    // sessionStorage.setItem('data_gl', JSON.stringify(datas));
                    var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                    sessionStorage.setItem('data_gl', compressedData);
                    _.each(datas['report_lines'], function(rep_lines) {
                        rep_lines['balance_amount'] = rep_lines.balance
                        if (rep_lines['balance_amount'] > 0){
                            rep_lines.debit = self.format_currency(datas['currency'],rep_lines.balance);
                            rep_lines.credit = self.format_currency(datas['currency'],0);
                        }
                        else if (rep_lines['balance_amount'] < 0){
                            rep_lines.debit = self.format_currency(datas['currency'],0);
                            rep_lines.credit = self.format_currency(datas['currency'],-rep_lines.balance);
                        }
                        else{
                            rep_lines.debit = self.format_currency(datas['currency'],0);
                            rep_lines.credit = self.format_currency(datas['currency'],0);   
                        }
                        rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                        _.each(rep_lines['move_lines'], function(move_line) {
                            move_line['balance_amount'] = move_line.balance
                            if (move_line['balance_amount'] > 0){
                                move_line.debit = self.format_currency(datas['currency'],move_line.balance);
                                move_line.credit = self.format_currency(datas['currency'],0);
                            }
                            else if (move_line['balance_amount'] < 0){
                                move_line.debit = self.format_currency(datas['currency'],0);
                                move_line.credit = self.format_currency(datas['currency'],-move_line.balance);
                            }
                            else{
                                move_line.debit = self.format_currency(datas['currency'],0);
                                move_line.credit = self.format_currency(datas['currency'],0);   
                            }
                            move_line.amount_currency = self.format_currency(datas['currency'],move_line.amount_currency);
                            move_line.balance = self.format_currency(datas['currency'],move_line.balance);
                        });
                    });

                        if (initial_render) {
                                self.$('.filter_view_tb').html(QWeb.render('GLFilterView', {
                                    filter_data: datas['filters'],
                                    title : datas['name'],
                                }));
                                if ($('.filter_date').data('value') == undefined){
                                    $('.filter_date_gl[data-value="this_month"]').click();
                                }
                                else{
                                    var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
                                    if (list_item_selected.length) {
                                        var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');
                                        if (filter_value == 'this_month'){
                                            $('.filter_date_gl[data-value="this_month"]').click();
                                        }
                                        else{
                                            $('.filter_date_gl[data-value="'+filter_value+'"]').click();
                                        }
                                    }
                                    $(".gl_filter_view").css('display', 'none');                                        
                                }
                                self.$el.find('.journals').select2({
                                    placeholder: ' Journals...',
                                });
                                self.$el.find('.account').select2({
                                    placeholder: ' Accounts...',
                                });
                                self.$el.find('.analytics').select2({
                                    placeholder: 'Analytic Accounts...',
                                });
                                self.$el.find('.analytic_tags').select2({
                                    placeholder: 'Analytic Tags...',
                                });
                                self.$el.find('.target_move').select2({
                                    placeholder: 'Target Move...',
                                });
                                self.$el.find('.all_account').select2({
                                    placeholder: 'All Account...',
                                });

                        }
                        var child=[];
                    if (!(datas.hasOwnProperty('currency'))) {
                        datas['currency'] = []
                    }

                    self.$('.table_view_tb').html(QWeb.render('GLTable', {

                                        report_lines : datas['report_lines'],
                                        filter : datas['filters'],
                                        currency : datas['currency'],
                                        credit_total : datas['credit_total'],
                                        debit_total : datas['debit_total'],
                                        debit_balance : datas['debit_balance'],
                                        all_account : datas.filters.all_account,
                                    }));
                    // data_gl = datas
                    data_gl = LZString.compressToUTF16(JSON.stringify(datas));
                    self.clear_lines();
                });

                    }
                catch (el) {
                    window.location.href
                    }
        },

        clear_lines: function() {
            // var obj = JSON.parse(sessionStorage.getItem('data_gl'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_gl')));
            for (var i = 0; i < obj['report_lines'].length; i++) {
                obj['report_lines'][i]['move_lines'] = [];
            }
            // sessionStorage.setItem('data_gl', JSON.stringify(obj));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_gl', compressedData);
        },

        apply_filter: function(event) {
            $(".active-filter, .clear-filter").css('display', 'block');
            $(".filter_content").css('display', 'none');

            event.preventDefault();
            var self = this;
            self.initial_render = false;

            var filter_data_selected = {};
            filter_data_selected.expand = false


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

            var analytic_tag_ids = []
            var analytic_tag_text = [];
            var analytic_tag_res = document.querySelectorAll("[id='analytic_tag_res']")                        
            var analytic_tag_list = $(".analytic_tags").select2('data')
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
                    analytic_tag_res[i].innerHTML = "All";
                } 
            }
            filter_data_selected.analytic_tag_ids = analytic_tag_ids



            
            var list_item_selected = false
            if ($('.filter_date').data('value') == undefined){
                list_item_selected = $('ul.o_date_filter_gl').find('li > a.selected');
            }
            else{
                list_item_selected = $('ul.o_date_filter').find('li > a.selected');
            }

            var dt;
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            filter_data_selected.date_from = "";
            filter_data_selected.date_to = "";
            if (list_item_selected.length) {
                var filter_value = false
                if ($('.filter_date').data('value') == undefined){
                    filter_value = $('ul.o_date_filter_gl').find('li > a.selected').parent().data('value');
                }
                else{
                    filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');
                }

                if (filter_value != "this_month") {
                    $(".date-filter").css('display', 'initial');
                }
                
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
                else if (filter_value == "today") {
                    filter_data_selected.date_from = moment().format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment().format('YYYY-MM-DD');
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

            if (filter_data_selected.journal_ids.length != 0) {
                $(".journals-filter").css('display', 'initial');
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

            if (filter_data_selected.all_account != "Off") {
                $(".all_account-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'account.general.ledger',
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
            filter_data_selected.expand = false

            $('.filter_date_gl[data-value="this_month"]').click();

            var journal_res = document.querySelectorAll("[id='journal_res']")
            for (var i = 0; i < journal_res.length; i++) {
                journal_res[i].value = "All"
                journal_res[i].innerHTML = "All";
            }
            filter_data_selected.journal_ids = []

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

            var analytic_tag_res = document.querySelectorAll("[id='analytic_tag_res']")
            for (var i = 0; i < analytic_tag_res.length; i++) {
                analytic_tag_res[i].value = "All"
                analytic_tag_res[i].innerHTML = "All";
            }
            filter_data_selected.analytic_tag_ids = []

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
            filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');

            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);
            filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');

            rpc.query({
                model: 'account.general.ledger',
                method: 'write',
                args: [
                    self.wizard_id, filter_data_selected
                ],
            }).then(function(res) {
            self.initial_render = true;
                self.load_data(self.initial_render);
            });
        },
    })
    return GeneralLedger;
});