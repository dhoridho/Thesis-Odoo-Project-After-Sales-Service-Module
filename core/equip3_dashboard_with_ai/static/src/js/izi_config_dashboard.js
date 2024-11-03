odoo.define('equip3_dashboard_with_ai.IZIConfigDashboard', function (require) {
    'use strict';

    var IZIAutocomplete = require('izi_dashboard.IZIAutocomplete');
    var IZIConfigDashboard = require('izi_dashboard.IZIConfigDashboard');
    var core = require('web.core');
    var _t = core._t;

    IZIConfigDashboard.include({
        _initDashboardAISearch: function() {
            var self = this;
            self.$dashboardSearchContainer.empty();
            self.$dashboardSearchContainer.append(`
                <input id="izi_dashboard_search" class="izi_wfull izi_mb5 izi_select2" placeholder="Input Keywords to Generate Analysis: Top Products By Sales Quantity in Pie Chart"/>
            `);
            new IZIAutocomplete(self, {
                elm: self.$dashboardSearchContainer.find(`#izi_dashboard_search`),
                multiple: true,
                placeholder: 'Dashboard Search',
                minimumInput: false,
                createSearchChoice: function(term, data) {
                    if ($(data).filter(function() {
                        return this.name.localeCompare(term) === 0;
                    }).length === 0) {
                        return {
                            id: 0,
                            name: term,
                            premium: 'Generate With AI',
                        };
                    }
                },
                tags: true,
                api: {
                    url: `${self.iziLabURL}/lab/analysis`,
                    method: 'POST',
                    body: {
                        'query': '',
                    },
                },
                params: {
                    textField: 'name',
                },
                onChange: function (values, name) {
                    console.log(values, name)
                    if (values.length > 0) {
                        var id = parseInt(values[0]);
                        var name = name;
                        self._getLabAnalysisConfig(id, name);
                    }
                },
                formatFunc: function format(item) { 
                    // return item[self.params.textField || 'name']; 
                    var material_icon_html = '';
                    var material_icon_html_right = '';
                    if (item['visual_type_icon']) {
                        if (item['category'] || item['premium']) {
                            material_icon_html = `<span class="material-icons">${item['visual_type_icon']}</span>`
                        } else {
                            material_icon_html_right = `<span class="material-icons">${item['visual_type_icon']}</span>`
                        }
                    }
                    var category_html = '';
                    if (item['category']) {
                        category_html = `<span>${item['category']}</span>`
                    }
                    var premium_html = '';
                    if (item['premium']) {
                        premium_html = `<span class="izi_dashboard_option_premium">${item['premium']}</span>`
                    }
                    return `<div class="izi_dashboard_option">
                        <div class="izi_dashboard_option_header">
                            <div class="izi_dashboard_option_name">
                                ${item['name']}
                            </div>
                            <div class="izi_dashboard_option_category">
                                ${material_icon_html}
                                ${category_html}
                            </div>
                        </div>
                        <div class="izi_dashboard_option_visual">
                            ${material_icon_html_right}
                        </div>
                    </div>`
                },
            });
        },

        _getLabAnalysisConfig: function (id, name) {
            var self = this;
            var body = {};
            self._rpc({
                model: 'izi.dashboard',
                method: 'action_get_lab_analysis_config',
                args: [self.selectedDashboard, id, name],
            }).then(function (res) {
                if (res && res.status == 200) {
                    self._initDashboard();
                    setTimeout(function () {
                        self.$viewDashboard.$grid.float(false);
                        self.$viewDashboard.$grid.compact();
                        self.$viewDashboard.$grid.float(true);
                        $('.o_content').animate({ scrollTop: $('.izi_view_dashboard').height() }, 3000);
                        if (self.$viewDashboard && self.$viewDashboard.$grid) {
                            var layout = self.$viewDashboard.$grid.save(false)
                            if (layout) {
                                self._rpc({
                                    model: 'izi.dashboard.block',
                                    method: 'ui_save_layout',
                                    args: [layout],
                                }).then(function (result) {
                                    if (result.status == 200) {
                                    }
                                })
                            }
                        }
                    }, 1000);
                } else {
                    self._initDashboard();
                    if (res.status == 401) {
                        var message_data = 'Your API key has expired. Please contact your administrator';
                        new swal('Need Access', message_data, 'warning');
                        self.do_action({
                            type: 'ir.actions.act_window',
                            name: _t('Need API Access'),
                            target: 'new',
                            res_model: 'izi.lab.api.key.wizard',
                            views: [[false, 'form']],
                            context: {},
                        },{
                            on_close: function(){
                                // self._initDashboard();
                            }
                        });
                    } else
                        var message_data = res.message;
                        var message_data = message_data.replace("odoo", "Hashmicro");
                        var message_data = message_data.replace("Odoo", "Hashmicro");
                        new swal('Error', message_data, 'error');
                }
            });
            
        },


    });
});