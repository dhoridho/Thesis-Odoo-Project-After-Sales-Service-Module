odoo.define('equip3_dashboard_with_ai.IZIAddAnalysis', function (require) {
    "use strict";


    var IZIAddAnalysis = require('izi_dashboard.IZIAddAnalysis');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    IZIAddAnalysis.include({
        _loadAnalysisItems: function (selectAnalysis=false) {
            var self = this;
            var args = {
                'category_id': self.selectedCategory || 0,
                'visual_type_id': self.selectedVisualType || 0,
                'keyword': self.keyword || '',
            }
            self.$analysisContainer.empty();
            self._rpc({
                model: 'izi.analysis',
                method: 'ui_get_all',
                args: [args],
            }).then(function (results) {
                self.allAnalysis = results;
                results.forEach(res => {
                    self.analysisById[res.id] = res;
                });
                // New Analysis
                var $new = `
                <div class="izi_new_analysis_item izi_select_item izi_select_item_blue">
                    <div class="izi_title" t-esc="name">New Analysis</div>
                    <div class="izi_subtitle" t-esc="source_table">
                        Create analysis from tables or queries
                    </div>
                    <div class="izi_select_item_icon">
                        <span class="material-icons">add</span>
                    </div>
                </div>
                `;
                self.$analysisContainer.append($new)
                // Render Analysis Item
                self.allAnalysis.forEach(analysis => {
                    var $content = $(QWeb.render('IZISelectAnalysisItem', {
                        name: `${analysis.name}`,
                        id: analysis.id,
                        table_id: analysis.table_id,
                        source_id: analysis.source_id,
                        table_name: analysis.table_name,
                        source_name: analysis.source_name,
                        source_table: '',
                        visual_type: analysis.visual_type,
                        visual_type_icon: analysis.visual_type_icon,
                        category_name: analysis.category_name,
                    }));
                    self.$analysisContainer.append($content)
                });
            })
        },


    });
});

odoo.define('equip3_dashboard_with_ai.IZISelectAnalysis', function (require) {
    "use strict";


    var IZISelectAnalysis = require('izi_dashboard.IZISelectAnalysis');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    IZISelectAnalysis.include({
        _onSelectAnalysisItem: function (ev) {
            var self = this;
            var id = $(ev.currentTarget).data('id');
            var name = $(ev.currentTarget).data('name');
            var source_table = '';
            var visual_type = $(ev.currentTarget).data('visual_type');
            self.selectedAnalysis = id;
            self.parent._selectAnalysis(id, name, source_table, visual_type);
            self.destroy();
        },
        _loadAnalysisItems: function (selectAnalysis=false) {
            var self = this;
            var args = {
                'category_id': self.selectedCategory || 0,
                'visual_type_id': self.selectedVisualType || 0,
                'keyword': self.keyword || '',
            }
            self.$analysisContainer.empty();
            self._rpc({
                model: 'izi.analysis',
                method: 'ui_get_all',
                args: [args],
            }).then(function (results) {
                self.allAnalysis = results;
                results.forEach(res => {
                    self.analysisById[res.id] = res;
                });
                // New Analysis
                var $new = `
                <div class="izi_new_analysis_item izi_select_item izi_select_item_blue">
                    <div class="izi_title" t-esc="name">New Analysis</div>
                    <div class="izi_subtitle" t-esc="source_table">
                        Create analysis from tables or queries
                    </div>
                    <div class="izi_select_item_icon">
                        <span class="material-icons">add</span>
                    </div>
                </div>
                `;
                self.$analysisContainer.append($new)
                // Render Analysis Item
                self.allAnalysis.forEach(analysis => {
                    var $content = $(QWeb.render('IZISelectAnalysisItem', {
                        name: `${analysis.name}`,
                        id: analysis.id,
                        table_id: analysis.table_id,
                        source_id: analysis.source_id,
                        table_name: analysis.table_name,
                        source_name: analysis.source_name,
                        source_table: '',
                        visual_type: analysis.visual_type,
                        visual_type_icon: analysis.visual_type_icon,
                        category_name: analysis.category_name,
                    }));
                    self.$analysisContainer.append($content)
                });
            })
        },


    });
});