odoo.define('equip3_accounting_reports.tax_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var trdata = []
    var sessionStorage = window.sessionStorage;

    window.click_num = 0;
    var TaxReport = AbstractAction.extend({
    template: 'TaxReportView',
        events: {
            'click .filter_date': '_onFilterDate',
            'click .filter_currency': '_onFilterCurrency',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click .view-account-move': 'view_acc_move',
            'click #apply_filter': 'apply_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click': '_onAnyWhereClick',
            'click .tr-line': 'show_drop_down',
            'click #collapse-button': 'collapse_all',
            'click .btn-sort': 'onClickSort',
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
            this.load_data(this.initial_render, sort, sort_type)
        },

        show_drop_down: function(event) {
            event.preventDefault();
            this.clear_lines();
            // var obj = JSON.parse(sessionStorage.getItem('data_tr'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tr')));
            var self = this;
            var account_id = $(event.currentTarget).data('tax-id');
            var td = $(event.currentTarget).next('tr').find('td');
            var data_tr = JSON.parse(LZString.decompressFromUTF16(trdata));
            if (td.length == 1) {                
                for (var i = 0; i < data_tr['report_lines'].length; i++) {
                    for (var j = 0; j < data_tr['report_lines'][i]['record_lines'].length; j++) {
                        if (account_id == data_tr['report_lines'][i]['record_lines'][j]['tax_id'] ){
                            obj['report_lines'][i]['record_lines'][j]['tax_lines'] = data_tr['report_lines'][i]['record_lines'][j]['tax_lines']
                            $(event.currentTarget).next('tr').find('td .tr-table-div').remove();
                            $(event.currentTarget).next('tr').find('td ul').after(
                                QWeb.render('TaxReportLines', {
                                    tax_rprt_line: data_tr['report_lines'][i]['record_lines'][j]['tax_lines'],
                                    currency : data_tr['currency'],
                                    total_line : data_tr['report_lines'][i]['record_lines'][j]['total_line'],
                                }))
                            $(event.currentTarget).next('tr').find('td ul li:first a').css({
                                'background-color': '#00ede8',
                                'font-weight': 'bold',
                            });
                        }
                    }
                }
                // sessionStorage.setItem('data_tr', JSON.stringify(obj));
                var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
                sessionStorage.setItem('data_tr', compressedData);
            }
        },

        collapse_all: function(event) {
            event.preventDefault();
            this.clear_lines();
            // var obj = JSON.parse(sessionStorage.getItem('data_tr'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tr')));
            var self = this;
            var action_title = self._title;
            var data_tr = JSON.parse(LZString.decompressFromUTF16(trdata));
            $('.table_view_tb .table_main_view > table > tbody > tr.tr-line[data-tax-id]').each(function(ev){
                let $row = $(this);
                if ($(event.currentTarget).hasClass('collapse-all')){
                    var account_id = $row.data('tax-id');
                    var td = $row.next('tr').find('td');
                    if (td.length == 1) {
                        for (var i = 0; i < data_tr['report_lines'].length; i++) {
                            for (var j = 0; j < data_tr['report_lines'][i]['record_lines'].length; j++) {
                                if (account_id == data_tr['report_lines'][i]['record_lines'][j]['tax_id'] ){
                                    obj['report_lines'][i]['record_lines'][j]['tax_lines'] = data_tr['report_lines'][i]['record_lines'][j]['tax_lines']
                                    $row.next('tr').find('td .tr-table-div').remove();
                                    $row.next('tr').find('td ul').after(
                                        QWeb.render('TaxReportLines', {
                                            tax_rprt_line: data_tr['report_lines'][i]['record_lines'][j]['tax_lines'],
                                            currency : data_tr['currency'],
                                            total_line : data_tr['report_lines'][i]['record_lines'][j]['total_line'],
                                        }))
                                    $row.next('tr').find('td ul li:first a').css({
                                        'background-color': '#00ede8',
                                        'font-weight': 'bold',
                                    });
                                    $row.removeClass('collapsed');
                                    $row.next('tr').addClass('show');
                                }
                            }
                        }
                        // sessionStorage.setItem('data_tr', JSON.stringify(obj));
                        var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
                        sessionStorage.setItem('data_tr', compressedData);
                    }
                } else {
                    $row.next('tr').find('td .tr-table-div').remove();
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
            }
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

        start: function() {
            var self = this;
            self.initial_render = true;
            rpc.query({
                model: 'tax.report',
                method: 'create',
                args: [{
                }]
            }).then(function(t_res) {
                self.wizard_id = t_res;
                self.load_data(self.initial_render);
            })
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
        load_data: function (initial_render=true, sort=false, sort_type=false) {
            var self = this;
            self.$(".categ").empty();
            $('div.o_action_manager').css('overflow-y', 'auto');
            try{
                var self = this;
                self._rpc({
                    model: 'tax.report',
                    method: 'view_report',
                    args: [[this.wizard_id]],
                    kwargs: {sort: sort, sort_type: sort_type},
                }).then(function(datas) {
                    // sessionStorage.setItem('data_tr', JSON.stringify(datas));
                    var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                    sessionStorage.setItem('data_tr', compressedData);
                    _.each(datas['report_lines'], function(rep_lines) {
                        rep_lines.tax_final_amount_total = self.format_currency(datas['currency'], rep_lines.tax_final_amount_total);
                        rep_lines.tax_final_gst_total = self.format_currency(datas['currency'], rep_lines.tax_final_gst_total);
                        rep_lines.tax_final_untaxed_amount_total = self.format_currency(datas['currency'], rep_lines.tax_final_untaxed_amount_total);
                        _.each(rep_lines.record_lines, function(rec_lines) {
                            rec_lines.amount_total = self.format_currency(datas['currency'], rec_lines.amount_total);
                            rec_lines.gst_total = self.format_currency(datas['currency'], rec_lines.gst_total);
                            rec_lines.untaxed_amount_total = self.format_currency(datas['currency'], rec_lines.untaxed_amount_total);
                            var total_lines = rec_lines.total_line;
                            total_lines.amount_total = self.format_currency(datas['currency'], total_lines.amount_total);
                            total_lines.gst_total = self.format_currency(datas['currency'], total_lines.gst_total);
                            total_lines.untaxed_amount_total = self.format_currency(datas['currency'], total_lines.untaxed_amount_total);
                            _.each(rec_lines.tax_lines, function(tax_line) {
                                tax_line.amount_total = self.format_currency(datas['currency'], tax_line.amount_total);
                                tax_line.tax_amount = self.format_currency(datas['currency'], tax_line.tax_amount);
                                tax_line.untaxed_amount = self.format_currency(datas['currency'], tax_line.untaxed_amount);
                            });
                        });
                    });
                    if (initial_render) {
                        self.$('.filter_view_tb').html(QWeb.render('TaxReportFilterView', {
                            filter_data: datas['filters'],
                            currencies: datas['currencies'],
                        }));
                        $('.filter_date[data-value="this_month"]').click();
                        self.$el.find('.account').select2({
                            placeholder: ' Accounts...',
                        });
                        self.$el.find('.target_move').select2({
                            placeholder: 'Target Move...',
                        });
                        self.$el.find('.companies').select2({
                            placeholder: 'Companies...',
                        });
                        self.$el.find('.branch').select2({
                            placeholder: 'Branch...',
                        });
                        self.$el.find('.taxes').select2({
                            placeholder: 'Taxes...',
                        });
                    }

                    var renderPromise = self.$('.table_view_tb').html(QWeb.render('TaxReportTable', {
                        report_lines : datas['report_lines'],
                        currency : datas['currency'],
                        total_lines: datas['total_lines']
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

                    data_tr = datas;
                    trdata = LZString.compressToUTF16(JSON.stringify(datas));
                    self.clear_lines();
                });
            }
            catch (el) {
                window.location.href
            }
        },

        clear_lines: function() {
            // var obj = JSON.parse(sessionStorage.getItem('data_tr'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tr')));
            for (var i = 0; i < obj['report_lines'].length; i++) {
                for (var j = 0; j < obj['report_lines'][i]['record_lines'].length; j++) {
                    obj['report_lines'][i]['record_lines'][j]['tax_lines'] = [];
                };
            };
            // sessionStorage.setItem('data_tr', JSON.stringify(obj));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_tr', compressedData);
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
            var model = $(event.currentTarget).data('model')
            rpc.query({
                    model: model,
                    method: 'search_read',
                    domain: [
                        ['id', '=', $(event.currentTarget).data('move-id')]
                    ],
                    fields: ['id'],
                    limit: 1,
                })
                .then(function(record) {
                    if (record.length > 0) {
                        show_acc_move(model, record[0].id);
                    } else {
                        show_acc_move(model, $(event.currentTarget).data('move-id'));
                    }
                });
        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            var action_title = self._title
            // var obj = JSON.parse(sessionStorage.getItem('data_tr'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tr')));
            var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'equip3_accounting_reports.tax_report',
                    'report_file': 'equip3_accounting_reports.tax_report',
                    'data': {
                        'report_data': obj
                    },
                    'context': {
                        'active_model': 'tax.report',
                        'landscape': 1,
                        'tax_pdf_report': true
                    },
                    'display_name': 'Tax Report',
                };
                return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            // var obj = JSON.parse(sessionStorage.getItem('data_tr'));
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_tr')));
            var action = {
                            'type': 'ir_actions_dynamic_xlsx_download',
                            'data': {
                                 'model': 'tax.report',
                                 'options': JSON.stringify(obj['filters']),
                                 'output_format': 'xlsx',
                                 'report_data': JSON.stringify(obj['report_lines']),
                                 'report_name': 'Tax Report',
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
            var span_res = document.querySelectorAll("[id='account_res']")
            var account_list = $(".account").select2('data')
            for (var i = 0; i < account_list.length; i++) {
                if(account_list[i].element[0].selected === true)
                    {account_ids.push(parseInt(account_list[i].id))
                if(account_text.includes(account_list[i].text) === false)
                    {account_text.push(account_list[i].text)
                }
                for (var j = 0; j < span_res.length; j++) {
                    span_res[j].value = account_text
                    span_res[j].innerHTML = span_res[j].value;
                }
                }
            }
            if (account_list.length == 0){
                for (var i = 0; i < span_res.length; i++) {
                    span_res[i].value = ""
                    span_res[i].innerHTML = "All";
                } 
            }
            filter_data_selected.account_ids = account_ids

            var company_ids = [];
            var company_text = [];
            var span_res = document.querySelectorAll("[id='company_res']")

            var company_list = $(".companies").select2('data')
            for (var i = 0; i < company_list.length; i++) {
                if(company_list[i].element[0].selected === true)
                    {company_ids.push(parseInt(company_list[i].id))
                if(company_text.includes(company_list[i].text) === false)
                    {company_text.push(company_list[i].text)
                }
                for (var j = 0; j < span_res.length; j++) {
                    span_res[j].value = company_text
                    span_res[j].innerHTML = span_res[j].value;
                }
                }
            }
            if (company_list.length == 0){
                for (var i = 0; i < span_res.length; i++) {
                    span_res[i].value = ""
                    span_res[i].innerHTML = "All";
                }
            }
            filter_data_selected.company_ids = company_ids

            var branch_ids = [];
            var branch_text = [];
            var span_res = document.querySelectorAll("[id='branch_res']")

            var branch_list = $(".branch").select2('data')
            for (var i = 0; i < branch_list.length; i++) {
                if(branch_list[i].element[0].selected === true)
                    {branch_ids.push(parseInt(branch_list[i].id))
                if(branch_text.includes(branch_list[i].text) === false)
                    {branch_text.push(branch_list[i].text)
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

            var tax_ids = [];
            var tax_text = [];
            var span_res = document.querySelectorAll("[id='tax_res']")
            var tax_list = $(".taxes").select2('data')
            for (var i = 0; i < tax_list.length; i++) {
                if(tax_list[i].element[0].selected === true)
                    {tax_ids.push(parseInt(tax_list[i].id))
                if(tax_text.includes(tax_list[i].text) === false)
                    {tax_text.push(tax_list[i].text)
                }
                for (var j = 0; j < span_res.length; j++) {
                    span_res[j].value = tax_text
                    span_res[j].innerHTML = span_res[j].value;
                }
                }
            }
            if (tax_list.length == 0){
                for (var i = 0; i < span_res.length; i++) {
                    span_res[i].value = ""
                    span_res[i].innerHTML = "All";
                } 
            }
            filter_data_selected.tax_ids = tax_ids

            var dt;
            var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            filter_data_selected.date_from = "";
            filter_data_selected.date_to = "";
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
            if (currency_item_selected.length) {
                var currency_value = $('ul.o_currency_filter').find('li > a.selected').parent().data('value');
                filter_data_selected.report_currency_id = currency_value;
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

            if (filter_data_selected.report_currency_id != undefined) {
                $(".currency-filter").css('display', 'initial');
            }
            if (filter_data_selected.account_ids.length != 0) {
                $(".accounts-filter").css('display', 'initial');
            }
            if (filter_data_selected.company_ids.length != 0) {
                $(".companies-filter").css('display', 'initial');
            }
            if (filter_data_selected.branch_ids.length != 0) {
                $(".branch-filter").css('display', 'initial');
            }
            if (filter_data_selected.tax_ids.length != 0) {
                $(".taxes-filter").css('display', 'initial');
            }
            if (filter_data_selected.target_move != "Posted") {
                $(".target-move-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'tax.report',
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
            filter_data_selected.report_currency_id = 12

            var account_res = document.querySelectorAll("[id='account_res']")
            for (var i = 0; i < account_res.length; i++) {
                account_res[i].value = "All"
                account_res[i].innerHTML = "All";
            }
            filter_data_selected.account_ids = []

            var comp_res = document.querySelectorAll("[id='company_res']")
            for (var i = 0; i < comp_res.length; i++) {
                comp_res[i].value = "All"
                comp_res[i].innerHTML = "All";
            }
            filter_data_selected.company_ids = []

            var branch_res = document.querySelectorAll("[id='branch_res']")
            for (var i = 0; i < branch_res.length; i++) {
                branch_res[i].value = "All"
                branch_res[i].innerHTML = "All";
            }
            filter_data_selected.branch_ids = []

            var tax_res = document.querySelectorAll("[id='tax_res']")
            for (var i = 0; i < tax_res.length; i++) {
                tax_res[i].value = "All"
                tax_res[i].innerHTML = "All";
            }
            filter_data_selected.tax_ids = []

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
                model: 'tax.report',
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
    core.action_registry.add("account_tax_report", TaxReport);
    return TaxReport;
});
