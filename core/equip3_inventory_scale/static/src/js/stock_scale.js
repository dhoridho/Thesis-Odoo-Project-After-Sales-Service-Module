odoo.define('equip3_inventory_scale.StockScale', function(require){

    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var fieldUtils = require('web.field_utils');
    var QWeb = core.qweb;

    var StockScaleAction = AbstractAction.extend({
        contentTemplate: "StockScale",
        hasControlPanel: false,

        events: {
            "click .o_increase": "_increaseScale",
            "click .o_decrease": "_decreaseScale",
            "click .o_input_button": "_onClickInputButton",
            "click .o_start_listen": "_onClickStartListen",
            "click .o_stop_listen": "_onClickStopListen",
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.precision = 2;
            this.dataURL = false;
            this.errMessage = false;
            this.scale = 0.0;
            this.context = action.context;

            this.scaleField = this.context.scale_qty;
            this.activeId = this.context.scale_res_id;
            this.activeModel = this.context.scale_res_model;
        },

        willStart: function(){
            var self = this;
            var urlProm = this._rpc({
                model: 'ir.config_parameter',
                method: 'get_param',
                args: ['equip3_inventory_scale.scale_url']
            }).then(function(dataURL){
                self.dataURL = dataURL;
            });

            var precProm = this._rpc({
                model: 'ir.config_parameter',
                method: 'get_param',
                args: ['equip3_inventory_scale.scale_precision'],
            }).then(function(precision){
                if (precision){
                    precision = parseInt(precision);
                } else {
                    precision = 2;
                }
                self.precision = precision;
            });

            var qtyProm = this._rpc({
                model: this.activeModel,
                method: 'read',
                args: [[this.activeId], [this.scaleField]]
            }).then(function(records){
                self.scale = records[0][self.scaleField];
            });
            return Promise.all([this._super.apply(this, arguments), urlProm, precProm, qtyProm]);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$scale = self.$el.find('.o_scale');
                self.$alert = self.$el.find('.o_alert');
                self._onClickStartListen();
            });
        },

        _listen: function(){
            var self = this;
            var time = moment.utc(moment().format('YYYY-MM-DD h:mm:ss'), 'YYYY-MM-DD h:mm:ss').format('YYYY-MM-DD h:mm:ss');
            
            $.ajax({
                type: 'POST',
                url: this.dataURL,
                cache: false,
                data: { 
                    time: time 
                },
            })
            .done(function(data){
                self.scale = parseFloat(data);
                self._updateScale();
                if (self.listening){
                    self._listen();
                }
            })
            .fail(function(data){
                self.errMessage = data.statusText;
                self._renderAlert();
            });
        },

        formatFloat(value){
            return fieldUtils.format.float(value, false, {digits: [false, this.precision]});
        },

        _updateScale: function(){
            this.$scale.text(this.formatFloat(this.scale));
        },

        _renderAlert: function(){
            var $alert = QWeb.render('StockSaleAlert', {widget: this});
            this.$alert.html($alert);
        },

        _increaseScale: function(ev){
            this.scale += 1 / (10 ** this.precision);
            this._updateScale();
        },

        _decreaseScale: function(ev){
            this.scale -= 1 / (10 ** this.precision);
            this._updateScale();
        },

        _onClickInputButton: function(ev){
            if (!this.activeId){
                return;
            }
            var self = this;
            var context = this.context;
            context.scaling = true;

            return this._rpc({
                model: this.activeModel,
                method: 'write',
                args: [this.activeId, {[this.scaleField]: this.scale}],
                context: context
            }).then(function(){
                return self._rpc({
                    model: self.activeModel,
                    method: 'on_scaled',
                    args: [[self.activeId]],
                    context: self.context
                }).then(function(action){
                    if (!action){
                        action = {type: 'ir.actions.act_window_close'};
                    }
                    return self.do_action(action);
                });
            });
        },

        _onClickStartListen: function(ev){
            this.listening = true;
            this._listen();
            $('.o_start_listen').hide();
            $('.o_stop_listen').show();
        },

        _onClickStopListen: function(ev){
            this.listening = false;
            $('.o_stop_listen').hide();
            $('.o_start_listen').show();
        },

        destroy: function(){
            this.listening = false;
            this._super.apply(this, arguments);
        }
    });

    core.action_registry.add('stock_scale_action', StockScaleAction);
    return StockScaleAction;

});