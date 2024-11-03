odoo.define('equip3_manuf_operations.MrpWorkcenterState', function(require){
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var rpc = require('web.rpc');

    var workcenterFormRenderer = FormRenderer.extend({
        /*_renderView: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                var state = self.state.data ? self.state.data.state : undefined;
                var stateLabels = _.filter(self.state.fields.state.selection, function(selection){
                    return selection[0] === state;
                });
                if (stateLabels.length){
                    var label = stateLabels[0][1];
                    var labelClass = 'bg-muted-hm';
                    if (state === 'available'){
                        labelClass = 'bg-success-hm';
                    } else if (state == 'waiting'){
                        label += ' (' + self.state.data.waiting_workorders_count + ')';
                        labelClass = 'bg-primary-hm';
                    } else if (state == 'running'){
                        label += ' (' + self.state.data.running_workorders_count + ')';
                        labelClass = 'bg-warning-hm';
                    } else if (state == 'blocked'){
                        labelClass = 'bg-danger-hm';
                    }
                    self.$el.find('div.oe_button_box').prepend('<div class="oe_workcenter_state ' + labelClass + '">' + label + '</div>');
                }
            });
        },*/

        events: _.extend({}, FormRenderer.prototype.events, {
            'click .oe_workcenter_state': '_workorder_click',
        }),
        _workorder_click: function(ev) {
            var self = this;
            var state = self.state.data ? self.state.data.state : undefined;
            var workcenter_id = self.state.data.id
            rpc.query({
                model: "mrp.workcenter",
                method: "action_production_view",
                args: [workcenter_id]
            }).then(function(data) {
                   if (state === 'waiting'){
                       return self.do_action({
                            type: data.type,
                            name: data.name,
                            res_model: data.res_model,
                            res_id: data.id,
                            domain: data.domain,
                            views: [[false, 'list'], [false, 'form']],
                            view_type: "list",
                            view_mode: data.view_mode,
                            target: data.target,
                       });
                   } else if (state == 'running'){
                         return self.do_action({
                            type: data.type,
                            name: data.name,
                            res_model: data.res_model,
                            res_id: data.id,
                            domain: data.domain,
                            views: [[false, 'list'], [false, 'form']],
                            view_type: "list",
                            view_mode: data.view_mode,
                            target: data.target,
                       });
                   };
            });
        },
    });

    var workcenterFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: workcenterFormRenderer,
        }),
    });
    
    viewRegistry.add('mrp_workcenter_state', workcenterFormView);
    
    return {
        workcenterFormRenderer: workcenterFormRenderer,
        workcenterFormView: workcenterFormView
    };
});