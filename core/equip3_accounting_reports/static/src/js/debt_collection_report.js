odoo.define('equip3_accounting_reports.debt_collection_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;

    var DebtCollectionReport = AbstractAction.extend({
        template: 'DebtCollection',
        events: {
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .clear-filter': 'clear_filter',
            'click #apply_filter': 'apply_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click .gl-line': 'show_drop_down',
            'click .view-account-move': 'view_acc_move',
        },

        init: function(parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.report_lines = action.report_lines;
            this.wizard_id = action.context.wizard | null;
        },

        start: function() {
            var self = this;
            self.initial_render = true;
            if (this.searchModel.config.domain.length != 0) {
                rpc.query({
                    model: 'debt.collection.report',
                    method: 'create',
                    args: [{
                        partner_ids : [this.searchModel.config.domain[0][2]]
                    }]
                }).then(function(t_res) {
                    self.wizard_id = t_res;
                    self.load_data(self.initial_render);
                })
            } else {
                rpc.query({
                    model: 'debt.collection.report',
                    method: 'create',
                    args: [{}]
                }).then(function(t_res) {
                    self.wizard_id = t_res;
                    self.load_data(self.initial_render);
                })
            }
        },

        load_data: function (initial_render = true) {
            var self = this;
            self.$(".categ").empty();
            $('div.o_action_manager').css('overflow-y', 'auto');

            try {
                var self = this;
                var action_title = self._title
                self._rpc({
                    model: 'debt.collection.report',
                    method: 'view_report',
                    args: [[this.wizard_id], action_title],
                }).then(function(datas) {
                    _.each(datas['report_lines'], function(rep_lines) {
                        rep_lines.invoice_amount = self.format_currency(datas['currency'],rep_lines.invoice_amount);
                        rep_lines.total_collection_amount = self.format_currency(datas['currency'],rep_lines.total_collection_amount);
                        rep_lines.debt_amount_due = self.format_currency(datas['currency'],rep_lines.debt_amount_due);
                    }); 

                    if (initial_render) {
                        self.$('.filter_view_tb').html(QWeb.render('DCFilterView', {
                            filter_data: datas['filters'],
                            title : datas['name'],
                        }));

                        $('.filter_date[data-value="this_financial_year"]').click();

                        self.$el.find('.customers').select2({
                            placeholder: ' Customers...',
                        });
                        self.$el.find('.pics').select2({
                            placeholder: ' Person in Charge...',
                        });
                        self.$el.find('.payments').select2({
                            placeholder: ' Payment Method...',
                        });
                        self.$el.find('.state').select2({
                            placeholder: ' Status...',
                        });
                    }

                    var child = [];
                    self.$('.table_view_tb').html(QWeb.render('DCTable', {
                        report_lines : datas['report_lines'],
                        filter : datas['filters'],
                        currency : datas['currency'],
                        invoice_amount : datas['invoice_amount'],
                        total_collection_amount : datas['total_collection_amount'],
                        debt_amount_due : datas['debt_amount_due']
                    }));
                });
            } catch (el) {
                window.location.href
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

        apply_filter: function(event) {
            $(".active-filter, .clear-filter").css('display', 'block');
            $(".filter_content").css('display', 'none');

            event.preventDefault();
            var self = this;
            self.initial_render = false;
            var filter_data_selected = {};

            var partner_ids = [];
            var partner_text = [];
            var partner_res = document.querySelectorAll("[id='partner_res']")            
            var partner_list = $(".customers").select2('data')

            for (var i = 0; i < partner_list.length; i++) {
                if (partner_list[i].element[0].selected === true) {
                    partner_ids.push(parseInt(partner_list[i].id))
                    if (partner_text.includes(partner_list[i].text) === false) {
                        partner_text.push(partner_list[i].text)
                    }
                    for (var j = 0; j < partner_res.length; j++) {
                        partner_res[j].value = partner_text
                        partner_res[j].innerHTML = partner_res[j].value;
                    }
                }
            }
            if (partner_list.length == 0) {
                for (var i = 0; i < partner_res.length; i++) {
                    partner_res[i].value = ""
                    partner_res[i].innerHTML = "All";
                } 
            }
            filter_data_selected.partner_ids = partner_ids

            var user_ids = [];
            var user_text = [];
            var user_res = document.querySelectorAll("[id='user_res']")            
            var user_list = $(".pics").select2('data')

            for (var i = 0; i < user_list.length; i++) {
                if (user_list[i].element[0].selected === true) {
                    user_ids.push(parseInt(user_list[i].id))
                    if (user_text.includes(user_list[i].text) === false) {
                        user_text.push(user_list[i].text)
                    }
                    for (var j = 0; j < user_res.length; j++) {
                        user_res[j].value = user_text
                        user_res[j].innerHTML = user_res[j].value;
                    }
                }
            }
            if (user_list.length == 0) {
                for (var i = 0; i < user_res.length; i++) {
                    user_res[i].value = ""
                    user_res[i].innerHTML = "All";
                } 
            }
            filter_data_selected.user_ids = user_ids

            var journal_ids = [];
            var journal_text = [];
            var journal_res = document.querySelectorAll("[id='journal_res']")            
            var journal_list = $(".payments").select2('data')

            for (var i = 0; i < journal_list.length; i++) {
                if (journal_list[i].element[0].selected === true) {
                    journal_ids.push(parseInt(journal_list[i].id))
                    if (journal_text.includes(journal_list[i].text) === false) {
                        journal_text.push(journal_list[i].text)
                    }
                    for (var j = 0; j < journal_res.length; j++) {
                        journal_res[j].value = journal_text
                        journal_res[j].innerHTML = journal_res[j].value;
                    }
                }
            }
            if (journal_list.length == 0) {
                for (var i = 0; i < journal_res.length; i++) {
                    journal_res[i].value = ""
                    journal_res[i].innerHTML = "All";
                } 
            }
            filter_data_selected.journal_ids = journal_ids

            if ($(".state").length) {
                var state_res = document.querySelectorAll("[id='state_res']")
                filter_data_selected.state = $(".state")[1].value
           
                for (var i = 0; i < state_res.length; i++) {
                    state_res[i].value = $(".state")[1].value

                    var state_string = ''
                    if (state_res[i].value == 'all') {
                        state_string = 'All'
                    } else if (state_res[i].value == 'on_progress') {
                        state_string = 'On Progress'
                    } else if (state_res[i].value == 'wait_for_payment') {
                        state_string = 'Collection Payment'
                    } else if (state_res[i].value == 'done') {
                        state_string = 'Done'
                    }
                    state_res[i].innerHTML = state_string;
                    
                    if ($(".state")[1].value == "") {
                        state_res[i].innerHTML = "All";
                    }
                }
            }

            var dt;
            var list_item_selected = $('ul.o_date_filter').find('li > a.selected');
            var currency_item_selected = $('ul.o_currency_filter').find('li > a.selected');
            filter_data_selected.date_from = "";
            filter_data_selected.date_to = "";
            if (list_item_selected.length) {
                var filter_value = $('ul.o_date_filter').find('li > a.selected').parent().data('value');

                if (filter_value != "this_financial_year") {
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

            if (filter_data_selected.partner_ids.length != 0) {
                $(".customer-filter").css('display', 'initial');
            }
            if (filter_data_selected.user_ids.length != 0) {
                $(".pic-filter").css('display', 'initial');
            }
            if (filter_data_selected.journal_ids.length != 0) {
                $(".payment-filter").css('display', 'initial');
            }
            if (filter_data_selected.state != "all") {
                $(".state-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'debt.collection.report',
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

            $('.filter_date[data-value="this_financial_year"]').click();

            var partner_res = document.querySelectorAll("[id='partner_res']")
            for (var i = 0; i < partner_res.length; i++) {
                partner_res[i].value = "All"
                partner_res[i].innerHTML = "All";
            }
            filter_data_selected.partner_ids = []

            var user_res = document.querySelectorAll("[id='user_res']")
            for (var i = 0; i < user_res.length; i++) {
                user_res[i].value = "All"
                user_res[i].innerHTML = "All";
            }
            filter_data_selected.user_ids = []

            var journal_res = document.querySelectorAll("[id='journal_res']")
            for (var i = 0; i < journal_res.length; i++) {
                journal_res[i].value = "All"
                journal_res[i].innerHTML = "All";
            }
            filter_data_selected.journal_ids = []

            var state_res = document.querySelectorAll("[id='state_res']")
            for (var i = 0; i < state_res.length; i++) {
                state_res[i].value = "all"
                state_res[i].innerHTML = "All"
            }
            var state_selection = document.getElementById('state');
            for (var i = 0; i < state_selection.options.length; i++) {
                state_selection.options[i].selected = false;
            }
            filter_data_selected.state = "all"

            var search_choice = document.querySelectorAll(".select2-search-choice")
            for (var i = 0; i < search_choice.length; i++) {
                search_choice[i].remove()
            }
            var chosen = document.querySelectorAll(".select2-chosen")
            for (var i = 0; i < chosen.length; i++) {
                chosen[i].value = ""
                chosen[i].innerHTML = ""
            }

            const currentYear = new Date().getFullYear();
            filter_data_selected.date_from = new Date(currentYear, 0, 1);
            filter_data_selected.date_to = new Date(currentYear, 11, 31);

            rpc.query({
                model: 'debt.collection.report',
                method: 'write',
                args: [
                    self.wizard_id, filter_data_selected
                ],
            }).then(function(res) {
                self.initial_render = true;
                self.load_data(self.initial_render);
            });
        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            var action_title = self._title
            self._rpc({
                model: 'debt.collection.report',
                method: 'view_report',
                args: [
                    [self.wizard_id], action_title
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir.actions.report',
                    'report_type': 'qweb-pdf',
                    'report_name': 'equip3_accounting_reports.debt_collection',
                    'report_file': 'equip3_accounting_reports.debt_collection',
                    'data': {
                        'report_data': data
                    },
                    'context': {
                        'active_model': 'debt.collection.report',
                        'landscape': 1,
                        'trial_pdf_report': true
                    },
                    'display_name': action_title,
                };
                self.do_action(action);
            });
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            self._rpc({
                model: 'debt.collection.report',
                method: 'view_report',
                args: [
                    [self.wizard_id], action_title
                ],
            }).then(function(data) {
                var action = {
                    'type': 'ir_actions_dynamic_xlsx_download',
                    'data': {
                        'model': 'debt.collection.report',
                        'options': JSON.stringify(data['filters']),
                        'output_format': 'xlsx',
                        'report_data': JSON.stringify(data['report_lines']),
                        'report_name': action_title,
                        'dfr_data': JSON.stringify(data),
                    },
                };
                return self.do_action(action);
            });
        },

        format_currency: function(currency, amount) {
            if (typeof(amount) != 'number') {
                amount = parseFloat(amount);
            }
            var formatted_value = amount.toLocaleString(currency[2],{
                minimumFractionDigits: 2
            })
            return formatted_value
        },

        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var offset = 0;
            var td = $(event.currentTarget).next('tr').find('td');
            if (td.length == 1) {
                var action_title = self._title
                self._rpc({
                    model: 'debt.collection.report',
                    method: 'view_report',
                    args: [
                        [self.wizard_id], action_title
                    ],
                }).then(function(data) {
                    _.each(data['report_lines'], function(rep_lines) {
                        _.each(rep_lines['debt_lines'], function(move_line) {
                            move_line.invoice_amount = self.format_currency(data['currency'],move_line.invoice_amount);
                            move_line.debt_amount_due = self.format_currency(data['currency'],move_line.debt_amount_due);
                            move_line.total_collection_amount = self.format_currency(data['currency'],move_line.total_collection_amount);
                        });
                    });

                    for (var i = 0; i < data['report_lines'].length; i++) {
                        if (account_id == data['report_lines'][i]['id']) {
                            $(event.currentTarget).next('tr').find('td .gl-table-div').remove();
                            $(event.currentTarget).next('tr').find('td ul').after(
                                QWeb.render('DebtSubSection', {
                                    debt_data: data['report_lines'][i]['debt_lines'],
                                    currency_symbol : data.currency[0],
                                    currency_position : data.currency[1],
                                })
                            )
                            $(event.currentTarget).next('tr').find('td ul li:first a').css({
                                'background-color': '#00ede8',
                                'font-weight': 'bold',
                            });
                        }
                    }
                });
            }
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
    });
    core.action_registry.add("d_c_r", DebtCollectionReport);
    return DebtCollectionReport;
});