odoo.define('equip3_manuf_other_operations.MrpMpsReproduce', function (require) {
'use strict';

    var concurrency = require('web.concurrency');
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var Dialog = require('web.Dialog');
    var field_utils = require('web.field_utils');
    var session = require('web.session');

    var QWeb = core.qweb;
    var _t = core._t;

    const defaultPagerSize = 20;

    var MrpMpsReproduce = AbstractAction.extend({
        template: 'MPSReplenishAction',
        contentTemplate: 'equip3_mrp_mps_replenish_wizard',

        events: {
            'change .o_mrp_mps_input_scheduled_date': '_onChangeCell',
            'change .o_mrp_mps_input_to_replenish': '_onChangeCell',
            'click .o_mrp_mps_produce': '_onClickProduce',
            'click .o_mrp_mps_request': '_onClickRequest',
            'click .o_mrp_mps_reset': '_onClickReset',
            'change .o_mps_select_inline': '_onChangeBOM',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.actionManager = parent;
            this.action = action;
            this.context = action.context;
            this.domain = [];

            this.formatFloat = field_utils.format.float;

            this.state = false;
            this.periods = [];

            this.active_ids = [];
            this.suggestedDates = [];
            this.estimatedDates = [];
            this.mutex = new concurrency.Mutex();

            this.searchModelConfig.modelName = 'equip.mrp.production.schedule';
        },

        willStart: function () {
            var self = this;
            var _super = this._super.bind(this);
            var args = arguments;

            var def_control_panel = this._rpc({
                model: 'ir.model.data',
                method: 'get_object_reference',
                args: ['equip3_manuf_other_operations', 'equip3_mrp_mps_search_view'],
                kwargs: {context: session.user_context},
                context: this.context
            })
            .then(function (viewId) {
                self.viewId = viewId[1];
            });

            var def_periods = this._rpc({
                model: 'res.company',
                method: 'date_range_to_str',
                args: [[session.company_id]],
                context: this.context
            })
            .then(function (periods) {
                self.periods = periods;
            });
            
            this.domain = this.context.produce_domain;
            var def_content = this._getState();

            return Promise.all([def_content, def_control_panel, def_periods]).then(function () {
                return _super.apply(self, args);
            });
        },

        start: async function () {
            var self = this;
            return this._super(...arguments).then(async () => {
                if (self.state.length == 0) {
                    self.$el.find('.o_mrp_mps_wizard').replaceWith($(QWeb.render('equip3_mrp_mps_nocontent_helper')));
                }
                self.$el.find('.o_cp_bottom_bottom').css('min-height', 0);
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Make an rpc to get the state and afterwards set the company, the
         * manufacturing period, the groups in order to display/hide the differents
         * rows and the state that contains all the informations
         * about production schedules and their forecast for each period.
         *
         * @private
         * @return {Promise}
         */
        _getState: function () {
            var self = this;
            return this._rpc({
                model: 'equip.mrp.production.schedule',
                method: 'search_read',
                args: [this.domain, ['id']],
                context: this.context
            }).then(function(ids){
                self.active_ids = ids.slice(0, defaultPagerSize).map(i => i.id);
                var scheduleIds = ids.map(i => i.id);
                return self._rpc({
                    model: 'equip.mrp.production.schedule',
                    method: 'get_production_schedule_view_state',
                    args: [scheduleIds],
                    context: self.context
                }).then(function(states){
                    self.state = states;
                    return states;
                })
            });
        },

        _getProductionScheduleState: function (productionScheduleId) {
            var self = this;
            return this._rpc({
                model: 'equip.mrp.production.schedule',
                method: 'get_production_schedule_view_state',
                args: [[productionScheduleId]],
                context: self.context
            }).then(function (states) {
                for (var i = 0; i < states.length; i++) {
                    var state = states[i];
                    var index =  _.findIndex(self.state, {id: state.id});
                    if (index >= 0) {
                        self.state[index] = state;
                    }
                    else {
                        self.state.push(state);
                    }
                }
                return states;
            });
        },

        /**
         * reload all the production schedules inside content. Make an rpc to the
         * server in order to get the updated state and render it.
         *
         * @private
         * @return {Promise}
         */
        _reloadContent: function () {
            var self = this;
            return this._getState().then(function (state) {
                if (state.length){
                    var $content = $(QWeb.render('equip3_mrp_mps_replenish_wizard', {
                        widget: {
                            formatFloat: self.formatFloat,
                            periods: self.periods,
                            state: state,
                        }
                    }));
                    $('.o_mrp_mps_wizard').replaceWith($content);
                } else {
                    $('.o_mrp_mps_wizard').append($(QWeb.render('equip3_mrp_mps_nocontent_helper')));
                }
            });
        },

        /**
         * Get the state with an rpc and render it with qweb. If the production
         * schedule is already present in the view replace it. Else append it at the
         * end of the table.
         *
         * @private
         * @param {Array} [productionScheduleIds] equip.mrp.production.schedule ids to render
         * @return {Promise}
         */
        _renderProductionSchedule: function (productionScheduleId) {
            var self = this;
            return this._getProductionScheduleState(productionScheduleId).then(function (states) {
                return self._renderState(states);
            });
        },

        _renderState: function (states) {
            for (var i = 0; i < states.length; i++) {
                var state = states[i];

                var $table = $(QWeb.render('equip3_mrp_mps_production_replenish', {
                    state: [state],
                    formatFloat: this.formatFloat,
                    periods: this.periods
                }));
                var $tbody = $('.o_mps_content_replenish[data-id='+ state.id +']');
                if ($tbody.length) {
                    $tbody.replaceWith($table);
                } else {
                    var $warehouse = false;
                    if ('warehouse_id' in state) {
                        $warehouse = $('.o_mps_content_replenish[data-warehouse_id='+ state.warehouse_id[0] +']');
                    }
                    if ($warehouse.length) {
                        $warehouse.last().append($table);
                    } else {
                        $('.o_mps_product_table_replenish').append($table);
                    }
                }
            }
            return Promise.resolve();
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        _actionProduce: function (ids, replenishOption, bomIds) {
            var self = this;
            this.mutex.exec(function () {
                return self._rpc({
                    model: 'equip.mrp.production.schedule',
                    method: 'action_replenish',
                    args: [ids, replenishOption, bomIds],
                    context: self.context
                }).then(function() {
                    return self.do_action({type: 'ir.actions.act_window_close'});
                });
            });
        },

        _actionRequest: function (ids, warehouseId, bomIds) {
            var self = this;
            this.mutex.exec(function () {
                return self._rpc({
                    model: 'equip.mrp.production.schedule',
                    method: 'action_request',
                    args: [ids, warehouseId, bomIds],
                    context: self.context
                }).then(function(wizardId) {
                    return self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'material.request.wizard',
                        res_id: wizardId,
                        views: [[false, 'form']],
                        target: 'new'
                    });
                });
            });
        },

        _onClickProduce: function (ev) {
            ev.stopPropagation();
            var $manufOrder = this.$el.find('#manufacturing_order');
            var replenishOption = 'MP';
            if ($manufOrder[0].checked){
                replenishOption = 'MO'
            }

            var $selectedBom = this.$el.find('select.o_mps_select_inline');

            var bomIds = {}
            $selectedBom.each(function() {
                bomIds[$(this).data('mps_id')] = $(this).val();
            });

            var ids = this.active_ids;
            this._actionProduce(ids, replenishOption, bomIds);
        },

        _onClickRequest: function (ev) {
            ev.stopPropagation();
            var warehouseId;
            if (this.state.length){
                warehouseId = this.state[0]['warehouse_id'][0];
            }

            var $selectedBom = this.$el.find('select.o_mps_select_inline');

            var bomIds = {}
            $selectedBom.each(function() {
                bomIds[$(this).data('mps_id')] = $(this).val();
            });

            var ids = this.active_ids;
            this._actionRequest(ids, warehouseId, bomIds);
        },

        _onChangeBOM: function(ev){
            var self = this;
            var current_val = $(ev.currentTarget).find("option:selected" ).val();
            self._rpc({
                model: 'equip.mrp.production.schedule',
                method: 'get_selected_bom_material',
                args: [[],current_val],
            }).then(function(data) {
                var curr_parent_tbl = $(ev.currentTarget).parents('.o_mps_content_replenish')
                $(curr_parent_tbl).find('tr[name="materials"]').remove()
                var th_count = $(curr_parent_tbl).find('tr[name="to_produce"]').children()
                $.each(data, function(key,valueObj){
                    $.each(data[key], function(index, value){
                        var html = "<tr name='materials'><th><span data-placement='bottom' title='Material Name'>"+value[0]+" <span>("+value[2]+ ")</span></span></th>";
                        for (var i = 1; i!=th_count.length;i++) {
                            var curr_to_produce_val = value[1] * parseFloat($(th_count[i]).find('input').val())
                            html = html + "<th><div class='main_qty' style='display:none;'>"+value[1]+"</div><div class='text-right'><span>"+curr_to_produce_val.toFixed(2)+"</span></div></th>";
                        }
                        html = html + "</tr>";
                        curr_parent_tbl.append(html);
                    });
                });
            })
        },

        _writeForecast: function (forecastId, fieldName, fieldEdited, fieldValue) {
            var self = this;
            function doIt() {
                self.mutex.exec(function () {
                    return self._rpc({
                        model: 'equip.mrp.product.forecast',
                        method: 'write',
                        args: [[forecastId], {
                            [fieldName]: fieldValue,
                            [fieldEdited]: false
                        }],
                        context: self.context
                    }).then(function () {
                        self._reloadContent();
                    });
                });
            }
            Dialog.confirm(this, _t("Are you sure you want to reset this record ?"), {
                confirm_callback: doIt,
            });
        },

        _onClickReset: function (ev) {
            ev.preventDefault();
            var $target = $(ev.target);
            var resetField = $target.data('reset');
            var forecastId = $target.data('forecast_id');
            var isEdited = $target.data(resetField + '_edited');

            if (forecastId && isEdited){
                var fieldName = resetField;
                var fieldValue = false;
                var fieldEdited = resetField + '_edited';
                if (resetField === 'forecasted_demand' || resetField == 'to_replenish'){
                    fieldName = fieldName + '_qty';
                    fieldValue = 0.0;
                }
                this._writeForecast(forecastId, fieldName, fieldEdited, fieldValue);
            }
        },

        /**
         * Handles the change on a cell.
         *
         * @private
         * @param {jQuery.Event} ev
         */
        _onChangeCell: function (ev) {
            ev.stopPropagation();
            var $target = $(ev.target);
            var dateIndex = $target.data('date_index');
            var field = $target.data('field');
            var productionScheduleId = $target.closest('.o_mps_content_replenish').data('id');

            var newValue = $target.val();

            var bom_material_row = $(ev.currentTarget).parents('.o_mps_content_replenish').find('tr[name="materials"]')
            if (bom_material_row.length){
                _.each(bom_material_row, function(index){
                    var to_update_material_cell = $(index).children()[dateIndex+1]
                    var mno = $(to_update_material_cell).find('div.main_qty')[0].innerText.trim();
                    var update_qty = parseFloat(mno) *  parseFloat(newValue)

    //                $(to_update_material_cell).find('span').text(update_qty)
                    $($(to_update_material_cell).find('span'))[0].textContent = parseFloat(update_qty).toFixed(2)
    //                $(to_update_material_cell).find('span').text = parseFloat(update_qty)
                });
            }
    //        var to_update_material_cell = $(ev.currentTarget).parents('.o_mps_content_replenish').find('tr[name="materials"]').children()[dateIndex+1]
    //        var mno = $(to_update_material_cell).find('span')[0].innerText;
    //        var update_qty = parseFloat(mno) *  parseFloat(newValue)
    //        $(to_update_material_cell).find('span').text(parseFloat(update_qty))
    //        var mno = $(to_update_material_cell).find('div.main_qty')[0].innerText.trim();
    //        var update_qty = parseFloat(mno) *  parseFloat(newValue)
    //        $(to_update_material_cell).find('span').text(update_qty)

            var isValid;
            if (field === 'forecasted_demand' || field === 'to_replenish'){
                newValue = parseFloat(newValue);
                isValid = !isNaN(newValue);
            } else {
                isValid = Date.parse(newValue);
                newValue = newValue.replace('T', ' ');
            }

            if (!isValid){
                this._backToState(productionScheduleId);
            } else {
                this._saveQuantity(productionScheduleId, dateIndex, newValue, field);
            }
        },

        _backToState: function (productionScheduleId) {
            var state = _.where(_.flatten(_.values(this.state)), {id: productionScheduleId});
            return this._renderState(state);
        },

        /**
         * Save the forecasted quantity and reload the current schedule in order
         * to update its To Replenish quantity and its safety stock (current and
         * future period). Also update the other schedules linked by BoM in order
         * to update them depending the indirect demand.
         *
         * @private
         * @param {Object} [productionScheduleId] equip.mrp.production.schedule Id.
         * @param {Integer} [dateIndex] period to save (column number)
         * @param {Float} [forecastQty] The new forecasted quantity
         * @return {Promise}
         */
        _saveQuantity: function (productionScheduleId, dateIndex, newValue, field) {
            var self = this;
            this.mutex.exec(function () {
                return self._rpc({
                    model: 'equip.mrp.production.schedule',
                    method: 'set_forecast_values',
                    args: [productionScheduleId, dateIndex, newValue, field],
                    context: self.context
                }).then(function () {
                    return self._renderProductionSchedule(productionScheduleId).then(function () {
                        return self._focusNextInput(productionScheduleId, dateIndex, 'demand_forecast');
                    });
                });
            });
        },

        _focusNextInput: function (productionScheduleId, dateIndex, inputName) {
            var tableSelector = '.o_mps_content_replenish[data-id=' + productionScheduleId + ']';
            var rowSelector = 'tr[name=' + inputName + ']';
            var inputSelector = 'input[data-date_index=' + (dateIndex + 1) + ']';
            return $([tableSelector, rowSelector, inputSelector].join(' ')).select();
        },
    });

    core.action_registry.add('equip3_mrp_mps_action_replenish', MrpMpsReproduce);

    return MrpMpsReproduce;

});
