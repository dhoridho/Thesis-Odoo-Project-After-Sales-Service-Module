odoo.define('equip3_accounting_budget.purchase_budget_report', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;
    var data_purchase_budget = []
    var sessionStorage = window.sessionStorage;

    var PurchaseBudgetReport = AbstractAction.extend({
        template: 'PurchaseBudgetReportTemp',
        events: {
            'click #apply_filter': 'apply_filter',
            'click .clear-filter': 'clear_filter',
            'click #pdf': 'print_pdf',
            'click #xlsx': 'print_xlsx',
            'click .gl-line': 'show_drop_down',
            'click': '_onAnyWhereClick',
            'click #o_equip_filter_dropdown': '_onClickFilter',
            'click .filter_date': '_onFilterDate',
            'click .o_add_custom_filter': '_onCustomFilter',
            'click #collapse-button': 'collapse_all',
        },

        init: function(parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.wizard_id = action.context.wizard | null;
        },

        start: function() {
            var self = this;
            self.initial_render = true;
            rpc.query({
                model: 'purchase.budget.report',
                method: 'create',
                args: [{}]
            }).then(function(t_res) {
                self.wizard_id = t_res;
                self.load_data(self.initial_render);
            })
        },

        load_data: function (initial_render=true) {
            var self = this;
            self.$(".categ").empty();
            $('div.o_action_manager').css('overflow-y', 'auto');

            try {
                var self = this;
                self._rpc({
                    model: 'purchase.budget.report',
                    method: 'view_report',
                    args: [[this.wizard_id]],
                }).then(function(datas) {
                    var obj = JSON.parse(JSON.stringify(datas));
                    // _.each(obj['report_lines'], function(rep_lines, index) {
                    //     if (rep_lines.parent_budget_id != false) {
                    //         obj['report_lines'][index] = false
                    //     }
                    // });
                    sessionStorage.setItem('data_purchase_budget', JSON.stringify(obj));

                    _.each(datas['report_lines'], function(rep_lines) {
                        rep_lines.planned_amount_format_currency = self.format_currency(datas['currency'],rep_lines.planned_amount);
                        rep_lines.avail_amount_format_currency = self.format_currency(datas['currency'],rep_lines.avail_amount);
                        rep_lines.reserve_amount_format_currency = self.format_currency(datas['currency'],rep_lines.reserve_amount);
                        rep_lines.practical_amount_format_currency = self.format_currency(datas['currency'],rep_lines.practical_amount);
                        rep_lines.remaining_amount_format_currency = self.format_currency(datas['currency'],rep_lines.remaining_amount);
                    });

                    if (initial_render) {
                        self.$('.filter_view_tb').html(QWeb.render('PurchaseBudgetFilterView', {
                            filter_data: datas['filters'],
                            currencies: datas['currencies'],
                        }));
                        self.$el.find('.companies').select2({
                            placeholder: 'Company...',
                        });
                        self.$el.find('.branches').select2({
                            placeholder: 'Branch...',
                        });
                        self.$el.find('.analytic_tags').select2({
                            placeholder: 'Analytic Group...',
                        });
                    }

                    self.$('.table_view_tb').html(QWeb.render('PurchaseBudgetReportTable', {
                        report_lines : datas['report_lines'],
                        currency : datas['currency'],
                    }));

                    _.each(datas['report_lines'], function(rep_lines) {
                        if (rep_lines.is_parent == false) {
                            $(`tr[data-account-id="${rep_lines.id}"]`).removeAttr('data-toggle');
                        }
                    });

                    data_purchase_budget = datas
                    self.clear_lines();
                });
            } catch (el) {
                window.location.href
            }
        },

        format_currency: function(currency, amount) {
            if (typeof(amount) != 'number') {
                amount = parseFloat(amount);
            }
            var formatted_value = (parseInt(amount)).toLocaleString(currency[2],{
                minimumFractionDigits: 2
            })
            return formatted_value
        },

        print_pdf: function(e) {
            e.preventDefault();
            var self = this;
            var action_title = self._title;
            var obj = JSON.parse(sessionStorage.getItem('data_purchase_budget'));
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'equip3_accounting_budget.purchase_budget_report',
                'report_file': 'equip3_accounting_budget.purchase_budget_report',
                'data': {
                    'report_data': obj
                },
                'context': {
                    'active_model': 'purchase.budget.report',
                    'landscape': 1,
                },
                'display_name': 'Purchase Budget Report',
            };
            return self.do_action(action);
        },

        print_xlsx: function() {
            var self = this;
            var action_title = self._title
            var data = JSON.parse(sessionStorage.getItem('data_purchase_budget'));
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'purchase.budget.report',
                     'options': JSON.stringify(data['filters']),
                     'output_format': 'xlsx',
                     'report_data': JSON.stringify(data['report_lines']),
                     'report_name': 'Purchase Budget Report',
                     'dfr_data': JSON.stringify(data),
                },
            };
            return self.do_action(action);
        },

        show_drop_down: function(event) {
            event.preventDefault();
            var self = this;
            var account_id = $(event.currentTarget).data('account-id');
            var account_name = $(event.currentTarget).data('account-name');
            var obj = JSON.parse(sessionStorage.getItem('data_purchase_budget'));

            _.each(data_purchase_budget['report_lines'], function(rep_lines) {
                _.each(rep_lines['child_lines'], function(child_line) {
                    child_line.planned_amount_format_currency = self.format_currency(data_purchase_budget['currency'],child_line.planned_amount);
                    child_line.avail_amount_format_currency = self.format_currency(data_purchase_budget['currency'],child_line.avail_amount);
                    child_line.reserve_amount_format_currency = self.format_currency(data_purchase_budget['currency'],child_line.reserve_amount);
                    child_line.practical_amount_format_currency = self.format_currency(data_purchase_budget['currency'],child_line.practical_amount);
                    child_line.remaining_amount_format_currency = self.format_currency(data_purchase_budget['currency'],child_line.remaining_amount);
                });
            });

            for (var i = 0; i < data_purchase_budget['report_lines'].length; i++) {
                if (account_id == data_purchase_budget['report_lines'][i]['id'] && account_name == data_purchase_budget['report_lines'][i]['name']) {
                    $(event.currentTarget).next('tr').find('td .gl-table-div').remove();
                    $(event.currentTarget).next('tr').find('td ul').after(
                        QWeb.render('SubSectionalPB', {
                            report_lines : data_purchase_budget['report_lines'][i]['child_lines'],
                            currency : data_purchase_budget['currency'],
                        }))
                    $(event.currentTarget).next('tr').find('td ul li:first a').css({
                        'background-color': '#00ede8',
                        'font-weight': 'bold',
                    });

                    var paddingValue = parseInt($(event.currentTarget).find('td:first').css('padding-left'))
                    var childs_row = $(event.currentTarget).next().find('.first_row')

                    _.each(childs_row, function(child) {
                        $(child).css('padding-left', (paddingValue + 20) + 'px')
                    });
                    _.each(data_purchase_budget['report_lines'][i]['child_lines'], function(child) {
                        if (child.is_parent == false && child.is_monthly == false) {
                            $(`tr[data-account-id="${child.id}"]`).removeAttr('data-toggle');
                        }
                        if (child.is_monthly == true) {
                            $(`tr[data-account-id="${child.id}"][data-account-name="${child.name}"]`).removeAttr('data-toggle');
                            $(`tr[data-account-id="${child.id}"][data-account-name="${child.name}"]`).next('tr').remove();
                        }
                    });
                    
                    var fr_line = $(event.currentTarget).hasClass('collapsed');
                    if (fr_line) {
                        obj['report_lines'][i]['child_lines'] = data_purchase_budget['report_lines'][i]['child_lines']
                    } else {
                        obj['report_lines'][i]['child_lines'] = []
                    }
                }
            }
            sessionStorage.setItem('data_purchase_budget', JSON.stringify(obj));
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

        clear_lines: function() {
            var obj = JSON.parse(sessionStorage.getItem('data_purchase_budget'));
            for (var i = 0; i < obj['report_lines'].length; i++) {
                if (obj['report_lines'][i] != false) {
                    obj['report_lines'][i]['child_lines'] = []
                }
            }
            sessionStorage.setItem('data_purchase_budget', JSON.stringify(obj));
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
                } else if (filter_value == "this_quarter") {
                    dt = new moment();
                    filter_data_selected.date_from = dt.startOf('quarter').format('YYYY-MM-DD');
                    filter_data_selected.date_to = dt.endOf('quarter').format('YYYY-MM-DD');
                } else if (filter_value == "this_financial_year") {
                    dt = new Date();
                    var year = dt.getFullYear();
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');
                } else if (filter_value == "last_month") {
                    dt = new Date();
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    dt.setDate(1);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                } else if (filter_value == "last_quarter") {
                    dt = new Date();
                    dt.setMonth((moment(dt).quarter() - 1) * 3);
                    dt.setDate(0);
                    filter_data_selected.date_to = moment(dt).format('YYYY-MM-DD');
                    dt.setDate(1);
                    dt.setMonth(dt.getMonth() - 2);
                    filter_data_selected.date_from = moment(dt).format('YYYY-MM-DD');
                } else if (filter_value == "last_year") {
                    dt = new Date();
                    var year = dt.getFullYear() - 1;
                    filter_data_selected.date_to = moment([year]).endOf('year').format('YYYY-MM-DD');
                    filter_data_selected.date_from = moment([year]).startOf('year').format('YYYY-MM-DD');
                }
            } else if (list_item_selected.length == 0) {
                if ($("#date_from").val()) {
                    var dateString = $("#date_from").val();
                    filter_data_selected.date_from = dateString;
                }
                if ($("#date_to").val()) {
                    var dateString = $("#date_to").val();
                    filter_data_selected.date_to = dateString;
                }
            }

            var company_ids = [];
            var company_text = [];
            var span_res = document.querySelectorAll("[id='company_res']")
            var company_list = $(".companies").select2('data')
            for (var i = 0; i < company_list.length; i++) {
                if(company_list[i].element[0].selected === true) {
                    company_ids.push(parseInt(company_list[i].id))
                    if(company_text.includes(company_list[i].text) === false) {
                        company_text.push(company_list[i].text)
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
            var branch_list = $(".branches").select2('data')
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

            var analytic_tag_ids = []
            var analytic_tag_text = [];
            var analytic_tag_res = document.querySelectorAll("[id='analytic_tag_res']")                        
            var analytic_tag_list = $(".analytic_tags").select2('data')
            for (var i = 0; i < analytic_tag_list.length; i++) {
                if(analytic_tag_list[i].element[0].selected === true){
                    analytic_tag_ids.push(parseInt(analytic_tag_list[i].id))
                    if (analytic_tag_text.includes(analytic_tag_list[i].text) === false){
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

            if (filter_data_selected.company_ids.length != 0) {
                $(".companies-filter").css('display', 'initial');
            }
            if (filter_data_selected.branch_ids.length != 0) {
                $(".branches-filter").css('display', 'initial');
            }
            if (filter_data_selected.analytic_tag_ids.length != 0) {
                $(".analytic-tags-filter").css('display', 'initial');
            }

            rpc.query({
                model: 'purchase.budget.report',
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

            var date_selection = document.querySelectorAll(".filter_date .dropdown-item")
            for (var i = 0; i < date_selection.length; i++) {
                if (date_selection[i].classList.contains("selected")) {
                    date_selection[i].classList.remove("selected")
                }
            }
            $('.date_caret').text("");

            var company_res = document.querySelectorAll("[id='company_res']")
            for (var i = 0; i < company_res.length; i++) {
                company_res[i].value = "All"
                company_res[i].innerHTML = "All";
            }
            filter_data_selected.company_ids = []

            var branch_res = document.querySelectorAll("[id='branch_res']")
            for (var i = 0; i < branch_res.length; i++) {
                branch_res[i].value = "All"
                branch_res[i].innerHTML = "All";
            }
            filter_data_selected.branch_ids = []

            var analytic_tag_res = document.querySelectorAll("[id='analytic_tag_res']")
            for (var i = 0; i < analytic_tag_res.length; i++) {
                analytic_tag_res[i].value = "All"
                analytic_tag_res[i].innerHTML = "All";
            }
            filter_data_selected.analytic_tag_ids = []

            var dt;
            dt = new Date();
            dt.setDate(1);
            filter_data_selected.date_from = ""

            dt.setMonth(dt.getMonth() + 1);
            dt.setDate(0);
            filter_data_selected.date_to = ""

            rpc.query({
                model: 'purchase.budget.report',
                method: 'write',
                args: [
                    self.wizard_id, filter_data_selected
                ],
            }).then(function(res) {
                self.initial_render = true;
                self.load_data(self.initial_render);
            });
        },

        collapse_all: function(event) {
            event.preventDefault();
            var obj = JSON.parse(sessionStorage.getItem('data_purchase_budget'));
            $('.table_view_tb .table_main_view > table > tbody > tr.gl-line[data-account-id]').each(function(ev){
                let $row = $(this);
                if ($(event.currentTarget).hasClass('collapse-all')){
                    if ($row.hasClass('collapsed')) {
                        $row.click()
                    }
                    _.each($row.next().find('.collapsed'), function(child) {
                        $(child).click()
                    });
                } else {
                    if ($row.hasClass('collapsed') == false) {
                        $row.click()
                    }
                }
            });

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
    });
    core.action_registry.add("p_b_r", PurchaseBudgetReport);
    return PurchaseBudgetReport;
});