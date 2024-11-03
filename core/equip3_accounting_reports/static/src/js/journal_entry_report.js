odoo.define('equip3_accounting_reports.journal_entry_report', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var utils = require('web.utils');
    var QWeb = core.qweb;
    var _t = core._t;

    window.click_num = 0;
    var JournalEntryReport = AbstractAction.extend({
    template: 'journalentrytemplate',
    events: {
        'click #apply_filter': 'apply_filter',
        'click #pdf': 'print_pdf',
        'click #xlsx': 'print_xlsx'
    },
    init: function(parent, action) {
        this._super(parent, action);
        this.je_lines = action.je_lines;
        this.wizard_id = action.context.wizard | null;

    },
    start: function() {
        var self = this;
        self.initial_render = true;
        rpc.query({
            model: 'journal.entry.report',
            method: 'create',
            args: [{
            }]
        }).then(function(t_res) {
            self.wizard_id = t_res;
            self.load_data(self.initial_render);
        })
    },

    load_data: function (initial_render = true) {
        var self = this;
        var action_title = self._title;
        $('div.o_action_manager').css('overflow-y', 'auto');
        self.$(".categ").empty();
        try {
            var self = this;
            self._rpc({
                model: 'journal.entry.report',
                method: 'view_report',
                args: [[this.wizard_id], 'Journal Entry', action_title],
            }).then(function(datas) {
                if (initial_render) {
                    self.$('.filter_view_tb').html(QWeb.render('JournalReportFilterView', {
                        filter_data: datas['filters'],
                        title : datas['name'],
                    }));
                    self.$el.find('.journals').select2({
                        placeholder: ' Journals...',
                    });
                    self.$el.find('.moves').select2({
                        placeholder: ' moves...',
                    });
                    self.$el.find('.account').select2({
                        placeholder: ' Accounts...',
                    });                    
                    self.$el.find('.target_move').select2({
                        placeholder: 'Target Move...',
                    });
                    $(".target_move").click();
                }
                var child=[];
                self.$('.table_view_tb').html(QWeb.render('JournalReportTable', {
                    name : datas['name'],
                    report_lines : datas['report_lines'],
                    filter : datas['filters'],             
                    je_lines : datas['je_lines'],
                }));
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
        var action_title = self._title;
        self._rpc({
            model: 'journal.entry.report',
            method: 'view_report',
            args: [
                [self.wizard_id], 'Journal Entry', action_title
            ],
        }).then(function(data) {
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'equip3_accounting_reports.journal_entry_report',
                'report_file': 'equip3_accounting_reports.journal_entry_report',
                'data': {
                    'report_data': data,
                    'report_name': 'Journal Entry'
                },
                'context': {
                    'active_model': 'journal.entry.report',
                    'landscape': 1,
                    'js_report': true
                },
                'display_name': 'Journal Entry',
            };
            return self.do_action(action);
        });
    },

    print_xlsx: function() {
        var self = this;
        var action_title = self._title;
        self._rpc({
            model: 'journal.entry.report',
            method: 'view_report',
            args: [
                [self.wizard_id], 'Journal Entry', action_title
            ],
        }).then(function(data) {
            var action = {
                'type': 'ir_actions_dynamic_xlsx_download',
                'data': {
                     'model': 'journal.entry.report',
                     'options': JSON.stringify(data['filters']),
                     'output_format': 'xlsx',
                     'report_data': 'Journal Entry',
                     'report_name': 'Journal Entry',
                     'dfr_data': JSON.stringify(data),
                },
            };
            return self.do_action(action);
        });
    },
    apply_filter: function(event) {
        event.preventDefault();
        var self = this;
        self.initial_render = false;
        var filter_data_selected = {};
        var account_ids = [];
        var account_text = [];
        var account_res = document.getElementById("acc_res")
        var account_list = $(".account").select2('data')
        for (var i = 0; i < account_list.length; i++) {
            if(account_list[i].element[0].selected === true){
                account_ids.push(parseInt(account_list[i].id))
                if(account_text.includes(account_list[i].text) === false){
                    account_text.push(account_list[i].text)
                }
                account_res.value = account_text
                account_res.innerHTML = account_res.value;
            }
        }
        if (account_list.length == 0){
            account_res.value = ""
            account_res.innerHTML = "";
        }
        filter_data_selected.account_ids = account_ids

        var journal_ids = [];
        var journal_text = [];
        var journal_res = document.getElementById("journal_res")
        var journal_list = $(".journals").select2('data')
        for (var i = 0; i < journal_list.length; i++) {
            if(journal_list[i].element[0].selected === true){
                journal_ids.push(parseInt(journal_list[i].id))
                if(journal_text.includes(journal_list[i].text) === false){
                    journal_text.push(journal_list[i].text)
                }
                journal_res.value = journal_text
                journal_res.innerHTML = journal_res.value;
            }
        }
        if (journal_list.length == 0){
            journal_res.value = ""
            journal_res.innerHTML = "";
        }
        filter_data_selected.journal_ids = journal_ids

        if ($("#date_from").val()) {
            var dateString = $("#date_from").val();
            filter_data_selected.date_from = dateString;

        }
        if ($("#date_to").val()) {
            var dateString = $("#date_to").val();
            filter_data_selected.date_to = dateString;
        }

        if ($(".target_move").length) {
            var post_res = document.getElementById("post_res")
            filter_data_selected.target_move = $(".target_move")[1].value
            post_res.value = $(".target_move")[1].value
            post_res.innerHTML = post_res.value;
            if ($(".target_move")[1].value == "") {
                post_res.innerHTML = "posted";
            }
        }

        var move_ids = [];
        var move_text = [];
        var move_res = document.getElementById("move_res")
        var move_list = $(".moves").select2('data')
        for (var i = 0; i < move_list.length; i++) {
            if(move_list[i].element[0].selected === true){
                move_ids.push(parseInt(move_list[i].id))
                if(move_text.includes(move_list[i].text) === false){
                    move_text.push(move_list[i].text)
                }
                move_res.value = move_text
                move_res.innerHTML = move_res.value;
            }
        }
        if (move_list.length == 0){
            move_res.value = ""
            move_res.innerHTML = "";
        }
        filter_data_selected.move_ids = move_ids

        rpc.query({
            model: 'journal.entry.report',
            method: 'write',
            args: [
                self.wizard_id, filter_data_selected
            ],
        }).then(function(res) {
        self.initial_render = false;
            self.load_data(self.initial_render);
        });
    },

    });
    core.action_registry.add("je_r", JournalEntryReport);
    return JournalEntryReport;
});
