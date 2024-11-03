"use strict";

odoo.define('equip3_inventory_reports.StockPerWH', function (require) {
  "use strict";

  var core = require('web.core');

  var viewRegistry = require('web.view_registry');

  var ListView = require('web.ListView');

  var ListModel = require('web.ListModel');

  var ListRenderer = require('web.ListRenderer');

  var ListController = require('web.ListController');

  var SampleServer = require('web.SampleServer');

  var QWeb = core.qweb;
  var stockPerWhValues;
  SampleServer.mockRegistry.add('product.product/get_warehouse_based_product', function () {
    return Object.assign({}, stockPerWhValues);
  });
  var stockPerWhRenderer = ListRenderer.extend({
    events: _.extend({}, ListRenderer.prototype.events, {
      'change .o_stock_per_wh_dashboard': '_onWarehouseChange'
    }),
    _renderView: function _renderView() {
      var self = this;
      return this._super.apply(this, arguments).then(function () {
        var values = self.state.stockPerWhValues;
        var stock_per_wh = QWeb.render('equip3_inventory_reports.stock_per_wh_dashboard_list_header', {
          values: values
        });
        self.$el.prepend(stock_per_wh);
      });
    },
    _onWarehouseChange: function _onWarehouseChange(e) {
      e.preventDefault();
      var $action = $(e.currentTarget);
      this.trigger_up('shock_per_wh_open_action', {
        field_name: $action.attr('name'),
        field_value: e.currentTarget.value
      });
    }
  });
  var stockPerWhModel = ListModel.extend({
    /**
     * @override
     */
    init: function init() {
      this.stockPerWhValues = {};

      this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    __get: function __get(localID) {
      var result = this._super.apply(this, arguments);

      if (_.isObject(result)) {
        result.stockPerWhValues = this.stockPerWhValues[localID];
      }

      return result;
    },

    /**
     * @override
     * @returns {Promise}
     */
    __load: function __load() {
      return this._loadStockperWhDashboard(this._super.apply(this, arguments));
    },

    /**
     * @override
     * @returns {Promise}
     */
    __reload: function __reload() {
      return this._loadStockperWhDashboard(this._super.apply(this, arguments));
    },

    /**
     * @private
     * @param {Promise} super_def a promise that resolves with a dataPoint id
     * @returns {Promise -> string} resolves to the dataPoint id
     */
    _loadStockperWhDashboard: function _loadStockperWhDashboard(super_def) {
      var self = this;

      var dashboard_def = this._rpc({
        model: 'product.product',
        method: 'get_warehouse_values',
        args: [this.stockPerWhValues]
      });

      return Promise.all([super_def, dashboard_def]).then(function (results) {
        var id = results[0];
        stockPerWhValues = results[1];
        self.stockPerWhValues[id] = stockPerWhValues;
        return id;
      });
    }
  });
  var stockPerWhController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
      shock_per_wh_open_action: '_onStockperWhOpenAction'
    }),

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onStockperWhOpenAction: function _onStockperWhOpenAction(e) {
      var state, stockPerWhValues, context, res_ids;
      return regeneratorRuntime.async(function _onStockperWhOpenAction$(_context) {
        while (1) {
          switch (_context.prev = _context.next) {
            case 0:
              state = this.model.get(this.handle);
              stockPerWhValues = state.stockPerWhValues;

              if (e.data.field_name === "stock_per_wh_dashboard_warehouse_id") {
                stockPerWhValues.warehouse_id = e.data.field_value;
              }

              context = state.getContext();
              context['search_warehouse_id'] = stockPerWhValues.warehouse_id;
              _context.next = 7;
              return regeneratorRuntime.awrap(this._rpc({
                model: 'product.product',
                method: 'get_warehouse_based_product',
                context: context
              }));

            case 7:
              res_ids = _context.sent;
              context['compute_for_ids'] = res_ids;
              this.reload({
                context: context,
                domain: [["id", "in", res_ids]]
              });

            case 10:
            case "end":
              return _context.stop();
          }
        }
      }, null, this);
    }
  });
  var stockPerWhListViewDashboard = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
      Model: stockPerWhModel,
      Renderer: stockPerWhRenderer,
      Controller: stockPerWhController
    })
  });
  viewRegistry.add('stock_per_wh', stockPerWhListViewDashboard);
  return {
    stockPerWhModel: stockPerWhModel,
    stockPerWhRenderer: stockPerWhRenderer,
    stockPerWhController: stockPerWhController
  };
});