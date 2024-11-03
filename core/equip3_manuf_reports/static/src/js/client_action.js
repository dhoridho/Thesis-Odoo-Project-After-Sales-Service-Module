odoo.define('equip3_manuf_reports.ClientAction', function (require) {
'use strict';

const { ComponentWrapper } = require('web.OwlCompatibility');

var concurrency = require('web.concurrency');
var core = require('web.core');
var Pager = require('web.Pager');
var AbstractAction = require('web.AbstractAction');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

const defaultPagerSize = 20;

var ClientAction = AbstractAction.extend({

    contentTemplate: 'equip3_mrp_mps',
    hasControlPanel: true,
    loadControlPanel: true,
    withSearchBar: true,
    searchMenuTypes:['filter', 'groupBy', 'favorite'],

    custom_events: _.extend({}, AbstractAction.prototype.custom_events, {
        pager_changed: '_onPagerChanged',
    }),

    events: {
        'change .o_mrp_mps_input_forecasted_demand': '_onChangeCell',
        'change .o_mrp_mps_input_to_replenish': '_onChangeCell',
        'change .o_mrp_mps_warehouse': '_onChangeWarehouse',
        'click .o_mrp_mps_create': '_onClickCreate',
        'click .o_mrp_mps_procurement': '_onClickReplenish',
        'click .o_mrp_mps_unlink': '_onClickUnlink',
        'click .o_mrp_mps_reset': '_onClickReset'
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
        this.warehouseId = false;
        this.warehouseIds = [];

        this.active_ids = [];
        this.pager = false;
        this.recordsPager = false;
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
            args: ['equip3_manuf_reports', 'equip3_mrp_mps_search_view'],
            kwargs: {context: session.user_context},
            context: this.context
        })
        .then(function (viewId) {
            self.viewId = viewId[1];
        });

        var def_warehouses = this._rpc({
            model: 'stock.warehouse',
            method: 'search_read',
            fields: ['id', 'name'],
            context: this.context
        })
        .then(function (warehouseIds) {
            self.warehouseIds = warehouseIds;
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

        var def_domain = this._updateDomain(this.domain, [['warehouse_id', '=', this.warehouseId]]);
        var def_content = this._getState();

        return Promise.all([def_domain, def_content, def_control_panel, def_warehouses, def_periods]).then(function () {
            return _super.apply(self, args);
        });
    },

    start: async function () {
        await this._super(...arguments);
        if (this.state.length == 0) {
            this.$el.find('.o_mrp_mps').append($(QWeb.render('equip3_mrp_mps_nocontent_helper')));
        }
        await this.update_cp();
        await this.renderPager();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------


    /**
     * Create the Pager and render it. It needs the records information to determine the size.
     * It also needs the controlPanel to be rendered in order to append the pager to it.
     */
    renderPager: async function () {
        const currentMinimum = 1;
        const limit = defaultPagerSize;
        const size = this.recordsPager.length;

        this.pager = new ComponentWrapper(this, Pager, { currentMinimum, limit, size });

        await this.pager.mount(document.createDocumentFragment());
        const pagerContainer = Object.assign(document.createElement('span'), {
            className: 'o_mrp_mps_pager float-right',
        });
        pagerContainer.appendChild(this.pager.el);
        this.$pager = pagerContainer;

        this._controlPanelWrapper.el.querySelector('.o_cp_pager').append(pagerContainer);
    },

    /**
     * Update the control panel in order to add the 'replenish' button and a
     * custom menu with checkbox buttons in order to hide/display the different
     * rows.
     */
    update_cp: function () {
        var self = this;
        this.$buttons = $(QWeb.render('equip3_mrp_mps_control_panel_buttons'));
        this._update_cp_buttons();
        this.$buttons.find('.o_mrp_mps_replenish').on('click', self._onClickReplenish.bind(self));
        this.$buttons.find('.o_mrp_mps_create').on('click', self._onClickCreate.bind(self));
        return this.updateControlPanel({
            title: _t('Master Production Schedule'),
            cp_content: {
                $buttons: this.$buttons,
                $searchview: this.$searchView
            },
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Make an rpc to replenish the different schedules passed as arguments.
     * If the procurementIds list is empty, it replenish all the schedules under
     * the current domain. Reload the content after the replenish in order to
     * display the new forecast cells to run.
     *
     * @private
     * @param {Array} [productionScheduleId] equip.mrp.production.schedule id to
     * replenish or False if it needs to replenish all schedules in state.
     * @return {Promise}
     */
    _actionReplenish: function (productionScheduleId) {
        var self = this;

        var reloadMainContent = function(){
            return self._getState().then(function (state) {
                var $content = $(QWeb.render('equip3_mrp_mps', {
                    widget: {
                        state: state,
                        periods: self.periods,
                        formatFloat: self.formatFloat,
                        warehouseId: self.warehouseId,
                        warehouseIds: self.warehouseIds
                    }
                }));
                $('.o_mrp_mps').replaceWith($content);
                self._update_cp_buttons();
            });
        };
        this.mutex.exec(function () {
            return self.do_action('equip3_manuf_reports.equip3_action_mrp_mps_wizard', {
                on_close: reloadMainContent,
                additional_context: {produce_domain: self.domain, validate_estimated_date: true}
            });
        });
    },

    /**
     * Open the equip.mrp.production.schedule form view in order to create the record.
     * Once the record is created get its state and render it.
     *
     * @private
     * @return {Promise}
     */
    _createProduct: function () {
        var self = this;
        var exitCallback = function () {
            return self._rpc({
                model: 'equip.mrp.production.schedule',
                method: 'search_read',
                args: [[], ['id']],
                limit: 1,
                orderBy: [{name: 'id', asc: false}],
                context: self.context
            }).then(function (result) {
                if (result.length) {
                    return self._renderProductionSchedule(result[0].id);
                }
            });
        };
        this.mutex.exec(function () {
            return self.do_action('equip3_manuf_reports.equip3_action_mrp_mps_form_view', {
                on_close: exitCallback,
                additional_context: {'default_warehouse_id': self.warehouseId}
            });
        });
    },

    _getRecordIds: function () {
        var self = this;
        return this._rpc({
            model: 'equip.mrp.production.schedule',
            method: 'search_read',
            args: [this.domain],
            fields: ['id'],
            context: this.context
        }).then(function (ids) {
            self.recordsPager = ids;
            self.active_ids = ids.slice(0, defaultPagerSize).map(i => i.id);
            return ids;
        });
    },

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
            self.recordsPager = ids;
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
        return self._rpc({
            model: 'equip.mrp.production.schedule',
            method: 'get_impacted_schedule',
            args: [productionScheduleId, self.domain],
            context: this.context
        }).then(function (productionScheduleIds) {
            productionScheduleIds.push(productionScheduleId);
            return self._rpc({
                model: 'equip.mrp.production.schedule',
                method: 'get_production_schedule_view_state',
                args: [productionScheduleIds],
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
        this.$pager.remove();
        this.pager.destroy();

        var self = this;
        return this._getState().then(function (state) {
            if (state.length){
                var $content = $(QWeb.render('equip3_mrp_mps', {
                    widget: {
                        state: state,
                        formatFloat: self.formatFloat,
                        periods: self.periods,
                        warehouseId: self.warehouseId,
                        warehouseIds: self.warehouseIds
                    }
                }));
                $('.o_mrp_mps').replaceWith($content);
            } else {
                $('.o_mrp_mps').append($(QWeb.render('equip3_mrp_mps_nocontent_helper')));
            }
            self.renderPager();
            self._update_cp_buttons();
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
            var $newTbody = $(QWeb.render('equip3_mrp_mps_production_schedule', {
                periods: this.periods,
                state: [state],
                formatFloat: this.formatFloat,
            }));
            var $tbody = $('.o_mps_content[data-id='+ state.id +']');
            if ($tbody.length) {
                $tbody.replaceWith($newTbody);
            } else {
                $('.o_mps_product_table').append($newTbody);
            }
        }
        this._update_cp_buttons();
        return Promise.resolve();
    },

    /**
     * Unlink the production schedule and remove it from the DOM. Use a
     * confirmation dialog in order to avoid a mistake from the user.
     *
     * @private
     * @param {Object} [productionScheduleId] equip.mrp.production.schedule Id.
     * @return {Promise}
     */
    _unlinkProduct: function (productionScheduleId) {
        var self = this;
        function doIt() {
            self.mutex.exec(function () {
                return self._rpc({
                    model: 'equip.mrp.production.schedule',
                    method: 'unlink',
                    args: [productionScheduleId],
                    context: self.context
                }).then(function () {
                    self._reloadContent();
                });
            });
        }
        Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
            confirm_callback: doIt,
        });
    },

    _update_cp_buttons: function () {
        var recodsLen = Object.keys(this.state).length;
        var $addProductButton = this.$buttons.find('.o_mrp_mps_create');
        if (recodsLen) {
            $addProductButton.addClass('btn-secondary');
            $addProductButton.removeClass('btn-primary');
            this.el.querySelector('.o_mps_product_table').classList.remove('d-none');
        } else {
            $addProductButton.addClass('btn-primary');
            $addProductButton.removeClass('btn-secondary');
            this.el.querySelector('.o_mps_product_table').classList.add('d-none');
        }
        var toReplenish = _.filter(_.flatten(_.values(this.state)), function (mps) {
            if (_.where(mps.forecast_ids, {'to_replenish': true}).length) {
                return true;
            } else {
                return false;
            }
        });
        var $replenishButton = this.$buttons.find('.o_mrp_mps_replenish');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles the click on `add product` Event. It will display a form view in
     * order to create a production schedule and add it to the template.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCreate: function (ev) {
        ev.stopPropagation();
        this.$el.find('.o_view_nocontent').remove();
        this._createProduct();
    },

    /**
     * Handles the click on replenish button. It will call action_replenish with
     * all the Ids present in the view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickReplenish: function (ev) {
        ev.stopPropagation();
        var productionScheduleId = [];
        var $tbody = $(ev.target).closest('.o_mps_content');
        if ($tbody.length) {
            productionScheduleId = [$tbody.data('id')];
        }
        this._actionReplenish(productionScheduleId);
    },

    /**
     * Handles the click on unlink button. A dialog ask for a confirmation and
     * it will unlink the product.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnlink: function (ev) {
        ev.preventDefault();
        var productionScheduleId = $(ev.target).closest('.o_mps_content').data('id');
        this._unlinkProduct(productionScheduleId);
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

    _updateDomain: function(filterDomain, warehouseDomain){
        var domain = [];
        for (let arg of filterDomain){
            if (arg.length === 3){
                if (arg[0] !== 'warehouse_id'){
                    domain.push(arg);
                }
            } else {
                domain.push(arg);
            }
        }
        this.domain = domain.concat(warehouseDomain);
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

    _onPagerChanged: function (ev) {
        let { currentMinimum, limit } = ev.data;
        this.pager.update({ currentMinimum, limit });
        currentMinimum = currentMinimum - 1;
        this.active_ids = this.recordsPager.slice(currentMinimum, currentMinimum + limit).map(i => i.id);
        this._reloadContent();
    },

    /**
     * Handles the change on the search bar. Save the domain and reload the
     * content with the new domain.
     *
     * @private
     * @param {Object} searchQuery
     */
    _onSearch: function (searchQuery) {
        var warehouseDomain = [['warehouse_id', '=', this.warehouseId]];
        this._updateDomain(searchQuery.domain, warehouseDomain);
        this._reloadContent();
    },

    _onChangeWarehouse: function(ev){
        ev.preventDefault();
        var $target = $(ev.target);
        this.warehouseId = parseInt($target.val());
        this._updateDomain(this.domain, [['warehouse_id', '=', this.warehouseId]]);
        this._reloadContent();
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
        var productionScheduleId = $target.closest('.o_mps_content').data('id');

        var newValue = $target.val();
        var isValid;
        if (field == 'forecasted_demand' || field == 'to_replenish'){
            newValue = parseFloat(newValue);
            isValid = !isNaN(newValue);
        } else {
            isValid = Date.parse(newValue);
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
        var tableSelector = '.o_mps_content[data-id=' + productionScheduleId + ']';
        var rowSelector = 'tr[name=' + inputName + ']';
        var inputSelector = 'input[data-date_index=' + (dateIndex + 1) + ']';
        return $([tableSelector, rowSelector, inputSelector].join(' ')).select();
    },
});

core.action_registry.add('equip3_mrp_mps_client_action', ClientAction);

return ClientAction;

});
