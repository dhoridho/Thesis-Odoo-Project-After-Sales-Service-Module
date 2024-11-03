odoo.define('equip3_dashboard_with_ai.IZIConfigAnalysis', function (require) {
    'use strict';

    var IZIAutocomplete = require('izi_dashboard.IZIAutocomplete');
    var IZIConfigAnalysis = require('izi_dashboard.IZIConfigAnalysis');
    var core = require('web.core');
    var _t = core._t;

    IZIConfigAnalysis.include({

        _startLabAnalysisExplore: function(args) {
            var self = this;
            // Generate Dashboard
            new IZIAutocomplete(self, {
                'elm': self.$viewAnalysis.$('#izi_select2_dashboard_explore'),
                'multiple': false,
                'placeholder': 'Select Dashboard',
                'minimumInput': false,
                'params':  {
                    'model': 'izi.dashboard',
                    'textField': 'name',
                    'fields': ['id', 'name'],
                    'domain': [],
                    'limit': 10,
                    'sourceType': 'model',
                    'modelFieldValues': 'id',
                },
                'textField': 'name',
                'onChange': function(id, name) {
                    self.$viewAnalysis.selectedDashboardExplore = id;
                },
            })
            // 
            self.$viewAnalysis.$viewAnalysisExplore.closest('.izi_dialog').show();
            self.$viewAnalysis.$viewAnalysisExplore.empty();
            self.$viewAnalysis.selectedAnalysisExplores = [];
            self._rpc({
                model: 'izi.analysis',
                method: 'start_lab_analysis_explore',
                args: [self.selectedAnalysis],
                kwargs: args,
            }).then(function (result) {
                console.log('Success Start Analysis Explore', result);
                if (result && result.analysis_explores) {
                    result.analysis_explores.forEach(function (analysis) {
                        var $exploreVisual = new IZIViewVisual(self, {
                            'analysis_id': analysis.id,
                        });
                        var $exploreVisualContainer = $(`<div class="izi_view_analysis_explore_content"></div>`);
                        $(`<div class="izi_view_analysis_explore_container" data-analysis-id="${analysis.id}">
                            <div class="izi_view_analysis_explore_title">${analysis.name}</div>
                        </div>`).append($exploreVisualContainer).appendTo(self.$viewAnalysis.$viewAnalysisExplore);
                        $exploreVisual.appendTo($exploreVisualContainer);
                        self.$exploreVisuals.push($exploreVisual);
                    })
                } else if (result.status == 401) {
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
                    var message_data = result.message;
                    var message_data = message_data.replace("odoo", "Hashmicro");
                    var message_data = message_data.replace("Odoo", "Hashmicro");
                    
                    new swal('Error', message_data, 'error');
            })
        },


        
    });
});