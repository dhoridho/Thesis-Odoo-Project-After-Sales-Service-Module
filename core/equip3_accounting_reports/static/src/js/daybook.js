odoo.define('equip3_accounting_reports.daybook', function (require) {
    'use strict';

    var DayBook = require('dynamic_partner_daybook.daybook');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;
    var data_db = []
    var sessionStorage = window.sessionStorage;


    window.click_num = 0;

    DayBook.include({
        events: _.extend({}, DayBook.prototype.events, {
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click': '_onAnyWhereClick',
            'click #collapse-button': 'collapse_all',
            'click .btn-sort': 'onClickSort',
            'click .btn-sort-line': 'onClickSortLine',
        }),

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

            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            obj['report_lines'].sort(function(a, b) {
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

            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines.debit = self.format_currency(obj['currency'],rep_lines.debit);
                rep_lines.credit = self.format_currency(obj['currency'],rep_lines.credit);
                rep_lines.balance = self.format_currency(obj['currency'],rep_lines.balance);
            });

            var renderPromise = self.$('.table_view_tb').html(QWeb.render('Daytable', {
                report_lines : obj['report_lines'],
                filter : obj['filters'],
                currency : obj['currency'],
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

            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            var db_line = $(ev.currentTarget).closest('tr.collapse').siblings('.db-line');

            _.each(obj['report_lines'], function(rep_lines) {
                rep_lines['child_lines'].sort(function(a, b) {
                    if (sort_type == 'asc') {
                        return (a[sort] > b[sort]) ? 1 : ((a[sort] < b[sort]) ? -1 : 0);
                    } else {
                        return (b[sort] > a[sort]) ? 1 : ((b[sort] < a[sort]) ? -1 : 0);
                    }
                });
            });

            _.each(db_line, function(line) {
                _.each(obj['report_lines'], function(rep_lines) {
                    if ($(line).data('account-id') == rep_lines['id']) {
                        $(line).next('tr').find('td .db-table-div').remove();
                        $(line).next('tr').find('td ul').after(
                            QWeb.render('SubSectiondb', {
                                account_data: rep_lines['child_lines'],
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
        },

        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            _.each(data_db['report_lines'], function(rep_lines) {
                _.each(rep_lines['child_lines'], function(move_line) {
                    move_line.debit_format_currency = self.format_currency(data_db['currency'],move_line.debit);
                    move_line.credit_format_currency = self.format_currency(data_db['currency'],move_line.credit);
                    move_line.balance_format_currency = self.format_currency(data_db['currency'],move_line.balance);
                    if (move_line.partner_name == null) {
                        move_line.partner_name = ''
                    }
                });
            });
            for (var i = 0; i < data_db['report_lines'].length; i++) {
                if (account_id == data_db['report_lines'][i]['id'] ){
                    for (var j = 0; j < obj['report_lines'].length; j++) {
                        if (obj['report_lines'][j]['id'] == data_db['report_lines'][i]['id'] ){
                            if (!$(event.currentTarget).hasClass('collapsed')){
                                obj['report_lines'][j]['child_lines'] = [];
                            }
                            else {
                                obj['report_lines'][j]['child_lines'] = data_db['report_lines'][i]['child_lines'];
                            }
                        }
                    }
                    if (td.length == 1) {
                        $(event.currentTarget).next('tr').find('td .db-table-div').remove();
                        $(event.currentTarget).next('tr').find('td ul').after(
                            QWeb.render('SubSectiondb', {
                                account_data: data_db['report_lines'][i]['child_lines'],
                                currency_symbol : data_db.currency[0],
                                currency_position : data_db.currency[1],
                            }))
                        $(event.currentTarget).next('tr').find('td ul li:first a').css({
                            'background-color': '#00ede8',
                            'font-weight': 'bold',
                        });
                    }
                }
            }
            // sessionStorage.setItem('data_db', JSON.stringify(obj));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_db', compressedData);
        },

        collapse_all: function(event) {
            event.preventDefault();
            var self = this;
            var action_title = self._title;
            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            $('.table_view_tb .table_main_view > table > tbody > tr.db-line[data-account-id]').each(function(ev){
                let $row = $(this);
                if ($(event.currentTarget).hasClass('collapse-all')){
                    var account_id = $row.data('account-id');
                    var td = $row.next('tr').find('td');
                    if (td.length == 1) {
                        _.each(data_db['report_lines'], function(rep_lines) {
                            _.each(rep_lines['child_lines'], function(move_line) {
                                move_line.debit_format_currency = self.format_currency(data_db['currency'],move_line.debit);
                                move_line.credit_format_currency = self.format_currency(data_db['currency'],move_line.credit);
                                move_line.balance_format_currency = self.format_currency(data_db['currency'],move_line.balance);
                                if (move_line.partner_name == null) {
                                    move_line.partner_name = ''
                                }
                            });
                        });
                        for (var i = 0; i < data_db['report_lines'].length; i++) {
                            if (account_id == data_db['report_lines'][i]['id'] ){
                                for (var j = 0; j < obj['report_lines'].length; j++) {
                                    if (obj['report_lines'][j]['id'] == data_db['report_lines'][i]['id'] ){
                                        obj['report_lines'][j]['child_lines'] = data_db['report_lines'][i]['child_lines'];
                                    }
                                }
                                $row.next('tr').find('td .db-table-div').remove();
                                $row.next('tr').find('td ul').after(
                                    QWeb.render('SubSectiondb', {
                                        account_data: data_db['report_lines'][i]['child_lines'],
                                        currency_symbol : data_db.currency[0],
                                        currency_position : data_db.currency[1],
                                    }))
                                $row.next('tr').find('td ul li:first a').css({
                                    'background-color': '#00ede8',
                                    'font-weight': 'bold',
                                });
                                $row.removeClass('collapsed');
                                $row.next('tr').addClass('show');
                            }
                        }
                        // sessionStorage.setItem('data_db', JSON.stringify(obj));
                        var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
                        sessionStorage.setItem('data_db', compressedData);
                    }
                } else {
                    $row.next('tr').find('td .db-table-div').remove();
                    $row.addClass('collapsed');
                    $row.next('tr').removeClass('show');
                }
            });
            if ($(event.currentTarget).hasClass('collapse-all')){
                $(event.currentTarget).removeClass('collapse-all');
                $(event.currentTarget).addClass('collapsed-all');
                $(event.currentTarget).text('Collapse');
            }else{
                $(event.currentTarget).removeClass('collapsed-all');
                $(event.currentTarget).addClass('collapse-all');
                $(event.currentTarget).text('Expand');
                this.clear_lines()
            }
        },

        clear_lines: function() {
            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            for (var i = 0; i < data_db['report_lines'].length; i++) {
                obj['report_lines'][i]['child_lines'] = [];
            };
            // sessionStorage.setItem('data_db', JSON.stringify(obj));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_db', compressedData);
        },

        _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content') && !ev.target.className.includes('dropdown-item')) {
                if ($('.filter_content').css('display') != 'none') {
                    $(".filter_content").css('display', 'none');
                }
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

        _onClickFilter: function(ev) {
            ev.preventDefault();
            if ($('.filter_content').css('display') == 'none') {
                $(".filter_content").css('display', 'block');
            } else {
                $(".filter_content").css('display', 'none');
            }
            return false;
        },

        load_data: function (initial_render = true) {
            var self = this;
            self.$(".categ").empty();
            $('div.o_action_manager').css('overflow-y', 'auto');
            try{
                var self = this;
                self._rpc({
                    model: 'account.day.book',
                    method: 'view_report',
                    args: [[this.wizard_id]],
                }).then(function(datas) {
                    // sessionStorage.setItem('data_db', JSON.stringify(datas));
                    var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                    sessionStorage.setItem('data_db', compressedData);
                    _.each(datas['report_lines'], function(rep_lines) {
                        rep_lines.debit = self.format_currency(datas['currency'],rep_lines.debit);
                        rep_lines.credit = self.format_currency(datas['currency'],rep_lines.credit);
                        rep_lines.balance = self.format_currency(datas['currency'],rep_lines.balance);
                    });
                    if (initial_render) {
                        self.$('.filter_view_db').html(QWeb.render('DayFilterView', {
                            filter_data: datas['filters'],
                            title : datas['name'],
                        }));
                        $('.filter_date[data-value="this_month"]').click();
                        self.$el.find('.journals').select2({
                            placeholder: ' Journals...',
                        });
                        self.$el.find('.account').select2({
                            placeholder: ' Accounts...',
                        });
                        self.$el.find('.target_move').select2({
                            placeholder: 'Target Move...',
                        });
                    }
                    var child=[];
                    self.$('.table_view_tb').html(QWeb.render('Daytable', {
                        report_lines : datas['report_lines'],
                        filter : datas['filters'],
                        currency : datas['currency'],
                    }));
                    data_db = datas
                    self.clear_lines();
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
            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'dynamic_accounts_report.day_book',
                    'report_file': 'dynamic_accounts_report.day_book',
                    'data': {
                        'report_data': obj
                    },
                    'context': {
                        'active_model': 'account.day.book',
                        'landscape': 1,
                        'daybook_pdf_report': true
                    },
                    'display_name': 'Day Book',
                };

                return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            // var obj = JSON.parse(sessionStorage.getItem('data_db'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_db')));
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'account.day.book',
                     'options': JSON.stringify(obj['filters']),
                     'output_format': 'xlsx',
                     'report_data': JSON.stringify(obj['report_lines']),
                     'report_name': 'Day Book',
                     'dfr_data': JSON.stringify(obj),
                },
            };
            return self.do_action(action);
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
                if (account_list[i].element[0].selected === true) {
                    account_ids.push(parseInt(account_list[i].id))
                    if (account_text.includes(account_list[i].text) === false) {
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
                if (journal_list[i].element[0].selected === true) {

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
            if (list_item_selected.length) {
                var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');

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

            if (filter_data_selected.journal_ids.length != 0) {
                $(".journals-filter").css('display', 'initial');
            }
            if (filter_data_selected.account_ids.length != 0) {
                $(".accounts-filter").css('display', 'initial');
            }
            if (filter_data_selected.target_move != "Posted") {
                $(".target-move-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'account.day.book',
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
                model: 'account.day.book',
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
    return DayBook;

});