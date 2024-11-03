
odoo.define("equip3_hr_employee_appraisals.GraphRenderer", function(require){
    var nineBoxControlPanel = require('equip3_hr_employee_appraisals.ControlPanel');
    var PivotView = require("web.PivotView");

    var GraphRenderer = require("web.GraphRenderer");
    var GraphView = require('web.GraphView');

    var viewRegistry = require('web.view_registry');

    var core = require('web.core');
    var QWeb = core.qweb;

    var nineBoxPivotView = PivotView.extend({
        config: _.extend({}, PivotView.prototype.config, {
            ControlPanel: nineBoxControlPanel
        }),
    });

    var nineBoxGraphRenderer = GraphRenderer.extend({
        events: _.extend({}, GraphRenderer.prototype.events, {
            "click .box_nine_analysis": function(event) {
                var self = this;
                self.do_action({
                    name: "Nine Box Analysis",
                    view_mode: 'tree,form',
                    view_type: 'list',
                    views: [[false, 'list'],[false, 'form']],
                    views: [[false, 'list'],[false, 'form']],
                            domain:[
                        ['n_grid_result_id', '=', $(event.currentTarget).data('id')],['state','=','done']
                    ],
                    res_model: 'employee.performance',
                    type: 'ir.actions.act_window',
                    target: 'current',
                });
            },
        }),

        _renderBarChart: function(dataPoints){
            var self = this;
            this._super.apply(this, arguments);
            this._rpc({
                model: 'employee.performance',
                method: 'get_all_employee_performance_analysis',
                args:this.state.domains,
        
            }).then(async function (dataresult) {
                self.dataresult = dataresult
                self.$el.html(QWeb.render("NineAnalysisTemplate", {widget: self}));
                    $('div[role="toolbar"].o_cp_buttons').hide()
                $('.o_control_panel').css("min-height", "unset");
                $('.o_control_panel .o_group_by_menu').hide()
            })
                
        },
    });

    var nineBoxGraphView = GraphView.extend({
        config: _.extend({}, GraphView.prototype.config, {
            Renderer: nineBoxGraphRenderer,
            ControlPanel: nineBoxControlPanel,
        }),
    });

    viewRegistry.add('ninebox_pivot', nineBoxPivotView);
    viewRegistry.add('ninebox_graph', nineBoxGraphView);

    return {
        nineBoxPivotView: nineBoxPivotView,
        nineBoxGraphRenderer: nineBoxGraphRenderer,
        nineBoxGraphView: nineBoxGraphView
    }
});