odoo.define('equip3_accounting_reports.ageing', function (require) {
    'use strict';

    var PartnerAgeing = require('dynamic_accounts_report.ageing');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;
    var data_aeging = []
    var sessionStorage = window.sessionStorage;

    PartnerAgeing.include({
        events: _.extend({}, PartnerAgeing.prototype.events, {
            'click .filter_date': '_onFilterDate',
            'click .filter_currency': '_onFilterCurrency',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click': '_onAnyWhereClick',
        }),
 
        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var partner_id = $(event.currentTarget)[0].cells[0].innerText;
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_aging')));
            var aging = JSON.parse(LZString.decompressFromUTF16(data_aeging));
            
            _.each(aging['report_lines'][0], function(rep_lines) {
                _.each(rep_lines['child_lines'], function(child_line) {
                    child_line.amount_format_currency = self.format_currency(aging['currency'],child_line.amount);
                });
            });

            for (var i = 0; i < aging['report_lines'][0].length; i++) {
                if (account_id == aging['report_lines'][0][i]['partner_id'] ){
                    $(event.currentTarget).next('tr').find('td .gl-table-div').remove();
                    $(event.currentTarget).next('tr').find('td ul').after(
                        QWeb.render('SubSectional', {
                            account_data: aging['report_lines'][0][i]['child_lines'],
                            period_length: aging['filters']['period_length'],
                            section_list: aging['section_list'],
                            section_sub_list: aging['section_sub_list'],
                        }))
                    $(event.currentTarget).next('tr').find('td ul li:first a').css({
                        'background-color': '#00ede8',
                        'font-weight': 'bold',
                    });
                    
                    var fr_line = $(event.currentTarget).hasClass('collapsed');
                    if (fr_line) {
                        obj['report_lines'][0][i]['child_lines'] = aging['report_lines'][0][i]['child_lines']
                    }else {
                        obj['report_lines'][0][i]['child_lines'] = []
                    }
                }
            }
            // sessionStorage.setItem('data_aging', JSON.stringify(obj));
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_aging', compressedData);
        },

        _onAnyWhereClick: function(ev){
            if (!ev.target.className.includes('filter-content') && !ev.target.className.includes('dropdown-item') && !ev.target.className.includes('o_input')) {
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
        load_data: function (initial_render = true) {
            var self = this;
            self.$(".categ").empty();
            $('div.o_action_manager').css('overflow-y', 'auto');
            try{
                var self = this;
                self._rpc({
                    model: 'account.partner.ageing',
                    method: 'view_report',
                    args: [[this.wizard_id]],
                }).then(function(datas) {
                    // sessionStorage.setItem('data_aging', JSON.stringify(datas));
                    var compressedData = LZString.compressToUTF16(JSON.stringify(datas));
                    sessionStorage.setItem('data_aging', compressedData);
                    _.each(datas['report_lines'][0], function(rep_lines) {
                        rep_lines.total = self.format_currency(datas['currency'],rep_lines.total);
                        for (var i = datas['filters']['section_num']; i >= 0; i--) {
                            rep_lines[i] = self.format_currency(datas['currency'],rep_lines[i]);
                        }
                        rep_lines['direction'] = self.format_currency(datas['currency'],rep_lines['direction']);
                    });
                    for (var i = 0; i < datas['report_lines'][1].length; i++) {
                        datas['report_lines'][1][i] = self.format_currency(datas['currency'], datas['report_lines'][1][i]);
                    };

                    if (initial_render) {
                            self.$('.filter_view_tb').html(QWeb.render('AgeingFilterView', {
                                filter_data: datas['filters'],
                                currencies: datas['currencies'],
                            }));
                            self.$el.find('.partners').select2({
                                placeholder: ' Partners...',
                            });
                            self.$el.find('.category').select2({
                                placeholder: ' Partner Category...',
                            });
                            self.$el.find('.target_move').select2({
                                placeholder: ' Target Move...',
                            });
                            self.$el.find('.result_selection').select2({
                                placeholder: ' Account Type...',
                            });
                            self.$el.find('.branchs').select2({
                            placeholder: 'Branch...',
                            });

                    }
                    var child=[];
                    self.$('.table_view_tb').html(QWeb.render('Ageingtable', {
                        report_lines : datas['report_lines'],
                        move_lines :datas['report_lines'][2],
                        filter : datas['filters'],
                        currency : datas['currency'],
                        currencies: datas['currencies'],
                        period_length: datas['filters']['period_length'],
                        section_list: datas['section_list'],
                        section_num: datas['filters']['section_num'],
                    }));
                    data_aeging = LZString.compressToUTF16(JSON.stringify(datas));
                    self.clear_lines();
                });
            }
            catch (el) {
                window.location.href
            }
        },


        clear_lines: function() {
            var obj = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_aging')));
            for (var i = 0; i < obj['report_lines'][0].length; i++) {
                obj['report_lines'][0][i]['child_lines'] = []
            }
            var compressedData = LZString.compressToUTF16(JSON.stringify(obj));
            sessionStorage.setItem('data_aging', compressedData);
        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            var action_title = self._title
            var data = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_aging')));
            var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'dynamic_accounts_report.partner_ageing',
                    'report_file': 'dynamic_accounts_report.partner_ageing',
                    'data': {
                        'report_data': data
                    },
                    'context': {
                        'active_model': 'account.partner.ageing',
                        'landscape': 1,
                        'ageing_pdf_report': true

                    },
                    'display_name': 'Partner Ageing',
                };

                return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            var data = JSON.parse(LZString.decompressFromUTF16(sessionStorage.getItem('data_aging')));
            var action = {
                    'type': 'ir_actions_dynamic_xlsx_download',
                    'data': {
                         'model': 'account.partner.ageing',
                         'options': JSON.stringify(data['filters']),
                         'output_format': 'xlsx',
                         'report_data': JSON.stringify(data['report_lines']),
                         'report_name': 'Partner Ageing',
                         'dfr_data': JSON.stringify(data),
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

            var dt;
            var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            if (list_item_selected.length) {
                var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');
                if (filter_value != "today") {
                    $(".date-filter").css('display', 'initial');
                }

                if (filter_value == "today") {
                    filter_data_selected.date_from = moment().format('YYYY-MM-DD');
                }
                else if (filter_value == "last_month") {
                    dt = new Date();
                    dt.setDate(0);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "last_quarter") {
                    dt = new Date();
                    dt.setMonth((moment(dt).quarter() - 1) * 3);
                    dt.setDate(0);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                }
                else if (filter_value == "last_year") {
                    dt = new Date();
                    var year = dt.getFullYear() - 1;
                    filter_data_selected.date_from = moment([year]).endOf('year').format('YYYY-MM-DD');
                }
            }
            else if (list_item_selected.length == 0) {
                if ($("#date_from").val()) {
                    var dateString = $("#date_from").val();
                    filter_data_selected.date_from = dateString;
                }
            }

            if (currency_item_selected.length) {
                var currency_value = $('ul.o_currency_filter').find('li > a.selected').parent().data('value');
                filter_data_selected.report_currency_id = currency_value;
            }

            var partner_ids = [];
            var partner_text = [];
            var span_res = document.querySelectorAll("[id='partner_res']")
            var partner_list = $(".partners").select2('data')
            for (var i = 0; i < partner_list.length; i++) {
                if(partner_list[i].element[0].selected === true) {
                    partner_ids.push(parseInt(partner_list[i].id))
                    if(partner_text.includes(partner_list[i].text) === false) {
                        partner_text.push(partner_list[i].text)
                    }
                    for (var j = 0; j < span_res.length; j++) {
                        span_res[j].value = partner_text
                        span_res[j].innerHTML = span_res[j].value;
                    }
                }
            }
            if (partner_list.length == 0){
                for (var i = 0; i < span_res.length; i++) {
                    span_res[i].value = ""
                    span_res[i].innerHTML = "All";
                }
            }
            filter_data_selected.partner_ids = partner_ids

            var partner_category_ids = [];
            var partner_category_text = [];
            var span_res = document.querySelectorAll("[id='category_res']")            
            var category_list = $(".category").select2('data')
            for (var i = 0; i < category_list.length; i++) {
                if(category_list[i].element[0].selected === true) {
                    partner_category_ids.push(parseInt(category_list[i].id))
                    if(partner_category_text.includes(category_list[i].text) === false) {
                        partner_category_text.push(category_list[i].text)
                    }
                    for (var j = 0; j < span_res.length; j++) {
                        span_res[j].value = partner_category_text
                        span_res[j].innerHTML = span_res[j].value;
                    }
                }
            }
            if (category_list.length == 0){
                for (var i = 0; i < span_res.length; i++) {
                    span_res[i].value = ""
                    span_res[i].innerHTML = "All";
                }
            }
            filter_data_selected.partner_category_ids = partner_category_ids

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

            if ($(".result_selection").length) {
                var account_res = document.querySelectorAll("[id='account_res']")            

                filter_data_selected.result_selection = $(".result_selection")[1].value
                for (var j = 0; j < span_res.length; j++) {
                    account_res[j].value = $(".result_selection")[1].value
                    account_res[j].innerHTML = account_res[j].value;
                    if ($(".result_selection")[1].value == "") {
                        account_res[j].innerHTML="Receivable and Payable Accounts";
                    }
                }
            }

            if ($("#long_aging_input").length) {
                var long_aging_res = document.querySelectorAll("[id='long_aging_res']")
                filter_data_selected.period_length = $('#long_aging_input').val()
                
                for (var j = 0; j < long_aging_res.length; j++) {
                    long_aging_res[j].innerHTML = $('#long_aging_input').val();
                }
            }

            if ($("#section_input").length) {
                var section_res = document.querySelectorAll("[id='section_res']")
                filter_data_selected.section_num = $('#section_input').val()
                
                for (var j = 0; j < section_res.length; j++) {
                    section_res[j].innerHTML = $('#section_input').val();
                }
            }

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

            if (filter_data_selected.report_currency_id != undefined) {
                $(".currency-filter").css('display', 'initial');
            }
            if (filter_data_selected.partner_ids.length != 0) {
                $(".partners-filter").css('display', 'initial');
            }
            if (filter_data_selected.partner_category_ids.length != 0) {
                $(".partner-tag-filter").css('display', 'initial');
            }
            if (filter_data_selected.result_selection != "customer_supplier") {
                $(".account-type-filter").css('display', 'initial');
            }
            if (filter_data_selected.target_move != "Posted") {
                $(".target-move-filter").css('display', 'initial');
            }
            if (filter_data_selected.period_length != 30) {
                $(".long-aging-filter").css('display', 'initial');
            }
            if (filter_data_selected.section_num != 4) {
                $(".section-filter").css('display', 'initial');
            }
            if (filter_data_selected.branch_ids.length != 0) {
                $(".branchs-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'account.partner.ageing',
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

            $('.filter_date[data-value="today"]').click();

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

            var type_res = document.querySelectorAll("[id='account_res']")
            for (var i = 0; i < type_res.length; i++) {
                type_res[i].value = "customer_supplier"
                type_res[i].innerHTML = "Receivable and Payable Accounts";
            }
            filter_data_selected.result_selection = "customer_supplier"

            var partner_res = document.querySelectorAll("[id='partner_res']")
            for (var i = 0; i < partner_res.length; i++) {
                partner_res[i].value = "All"
                partner_res[i].innerHTML = "All";
            }
            filter_data_selected.partner_ids = []

            var category_res = document.querySelectorAll("[id='category_res']")
            for (var i = 0; i < category_res.length; i++) {
                category_res[i].value = "All"
                category_res[i].innerHTML = "All";
            }
            filter_data_selected.partner_category_ids = []

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

            var branch_res = document.querySelectorAll("[id='branch_res']")
            for (var i = 0; i < branch_res.length; i++) {
                branch_res[i].value = "All"
                branch_res[i].innerHTML = "All";
            }
            filter_data_selected.branch_ids = []

            var dt;
            dt = new Date();
            dt.setDate(1);
            filter_data_selected.date_from = moment().format('YYYY-MM-DD');

            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);

            var long_aging_res = document.querySelectorAll("[id='long_aging_res']")
            for (var i = 0; i < long_aging_res.length; i++) {
                $('#long_aging_input').val(30)
                long_aging_res[i].innerHTML = ""
            }
            filter_data_selected.period_length = 30

            var section_res = document.querySelectorAll("[id='section_res']")
            for (var i = 0; i < section_res.length; i++) {
                $('#section_input').val(4)
                section_res[i].innerHTML = ""
            }
            filter_data_selected.section_num = 4

            rpc.query({
                model: 'account.partner.ageing',
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
    
    return PartnerAgeing;

});