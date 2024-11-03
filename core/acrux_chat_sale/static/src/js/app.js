odoo.define("acrux_chat_sale.res_partner", (function(require) {
    "use strict";
    var session = require("web.session");
    return require("acrux_chat.form_view").extend({
        init: function(parent, options) {
            options && (options.model = "res.partner", options.record = options.res_partner), 
            this._super.apply(this, arguments), this.parent = parent, _.defaults(this.context, {
                default_mobile: this.parent.selected_conversation.number_format,
                default_phone: this.parent.selected_conversation.number_format,
                default_name: this.parent.selected_conversation.name,
                default_user_id: session.uid
            });
        },
        start: function() {
            return this._super().then((() => this.parent.product_search.minimize()));
        },
        recordChange: function(res_partner_id) {
            return Promise.all([ this._super(res_partner_id), this._rpc({
                model: this.parent.model,
                method: "save_res_partner",
                args: [ [ this.parent.selected_conversation.id ], res_partner_id ]
            }).then((result => {
                this.record = result.partner;
                let conv = this.parent.selected_conversation;
                conv.res_partner_id = result.partner, conv.partner_sellman_id = result.partner_sellman, 
                conv.partner_sellman_id[0] != session.uid ? (conv.$sellman.html(result.partner_sellman[1]), 
                conv.$sellman.attr("title", result.partner_sellman[1])) : (conv.$sellman.html(""), 
                conv.$sellman.attr("title", ""));
            })) ]);
        }
    });
})), odoo.define("acrux_chat_sale.sale_order", (function(require) {
    "use strict";
    var FormView = require("acrux_chat.form_view"), ResPartnerForm = require("acrux_chat_sale.res_partner");
    return FormView.extend({
        init: function(parent, options) {
            options && (options.model = "sale.order", options.record = options.sale_order), 
            this._super.apply(this, arguments), this.parent = parent, _.defaults(this.context, {
                default_partner_id: this.parent.selected_conversation.res_partner_id[0],
                default_team_id: this.parent.selected_conversation.team_id[0]
            });
        },
        start: function() {
            return this._super().then((() => this.makeProductDragAndDrop()));
        },
        _showAcruxFormView: function() {
            this._super().then((() => {
                if (this.moveSaleOrderNode(), !this.action.context.default_partner_id) {
                    let selector = "div.o_form_sheet > .o_notebook > .o_notebook_headers";
                    selector += " > ul.nav-tabs > li", this.acrux_form_widget.$(selector).eq(1).find("a").trigger("click");
                }
                this.$(".oe_title > h1").css("font-size", "20px");
            }));
        },
        recordUpdated: function(env) {
            return this._super(env).then((() => {
                if (this.moveSaleOrderNode(), env.currentId) {
                    let sale_order_key, patrner_key, partner_id, localData;
                    if (sale_order_key = this.acrux_form_widget.handle, localData = this.acrux_form_widget.model.localData, 
                    sale_order_key && (patrner_key = localData[sale_order_key].data.partner_id), patrner_key && (partner_id = localData[patrner_key].data), 
                    partner_id && partner_id.id && partner_id.id != this.parent.selected_conversation.res_partner_id[0]) if (this.parent.res_partner_form) this.parent.res_partner_form.recordChange(partner_id.id).then((() => {
                        this.parent.res_partner_form.destroy(), this.parent.res_partner_form = null;
                    })); else {
                        let tmp_widget = new ResPartnerForm(this.parent, {});
                        tmp_widget.recordChange(partner_id.id).then((() => {
                            tmp_widget.destroy();
                        }));
                    }
                }
            }));
        },
        recordChange: function(sale_order_id) {
            return Promise.all([ this._super(sale_order_id), this._rpc({
                model: this.parent.model,
                method: "save_sale_order",
                args: [ [ this.parent.selected_conversation.id ], sale_order_id ]
            }).then((result => {
                this.parent.selected_conversation.sale_order_id = result, this.record = result;
            })) ]);
        },
        makeProductDragAndDrop: function() {
            this.$el.css("padding", "0.5em"), this.$el.droppable({
                drop: (_event, ui) => {
                    if (this.parent.selected_conversation && "current" == this.parent.selected_conversation.status) {
                        let product = this.parent.product_search.find(ui.draggable.data("id"));
                        product && this.addProductToOrder(product);
                    }
                },
                accept: ".o_product_record",
                activeClass: "drop-active",
                hoverClass: "drop-hover"
            });
        },
        moveSaleOrderNode: function() {
            let main_group = this.acrux_form_widget.$("div.oe_title").next("div.o_group");
            main_group.length && main_group.prev().hasClass("oe_title") && (main_group = main_group.detach(), 
            main_group.appendTo(this.acrux_form_widget.$("div.o_form_sheet > div.o_notebook > div.tab-content > div.tab-pane").first().next()));
        },
        addProductToOrder: function(product) {
            "edit" != this.acrux_form_widget.mode ? this.acrux_form_widget._setMode("edit").then((() => {
                this.addRecord(product);
            })) : this.addRecord(product);
        },
        addRecord: function(product) {
            let sale_key, orderline, renderer, options;
            sale_key = this.acrux_form_widget.handle, renderer = this.acrux_form_widget.renderer, 
            orderline = renderer.allFieldWidgets[sale_key].find((x => "order_line" == x.name));
            let link_id = orderline.$el.parent().attr("id"), $link = this.$('a[href$="' + link_id + '"]'), wait = 0;
            $link.parent().hasClass("active") || ($link.trigger("click"), wait = 100), orderline.renderer.addCreateLine && setTimeout((() => {
                orderline.renderer.unselectRow().then((() => {
                    options = {
                        onSuccess: this.addProductToOrderLine.bind(this, product)
                    }, orderline.renderer.trigger_up("add_record", options);
                }));
            }), wait);
        },
        addProductToOrderLine: function(product) {
            let sale_key, orderline, renderer, orderline_id, product_id;
            sale_key = this.acrux_form_widget.handle, renderer = this.acrux_form_widget.renderer, 
            orderline = renderer.allFieldWidgets[sale_key].find((x => "order_line" == x.name)), 
            orderline_id = orderline.renderer.getEditableRecordID(), orderline_id && (product_id = orderline.renderer.allFieldWidgets[orderline_id], 
            product_id = product_id.find((x => "product_id" == x.name)), product_id && product_id.reinitialize({
                id: product.id,
                display_name: product.name
            }));
        }
    });
})), odoo.define("acrux_chat_sale.indicators", (function(require) {
    "use strict";
    var Widget = require("web.Widget"), ajax = require("web.ajax");
    return Widget.extend({
        jsLibs: [ "/web/static/lib/Chart/Chart.js" ],
        init: function(parent, options) {
            this._super.apply(this, arguments), this.parent = parent, this.options = _.extend({}, options), 
            this.context = _.extend({}, this.options.context), this.partner_id = this.options.partner_id, 
            this.chart = null;
        },
        willStart: function() {
            return Promise.all([ this._super(), ajax.loadLibs(this), this.getPartnerIndicator() ]);
        },
        start: function() {
            return this._super().then((() => this._initRender()));
        },
        _initRender: function() {
            return this.month_last_sale_data && this.$el.append(this.graph_6last_sale()), this.html_last_sale && this.$el.append(this.html_last_sale), 
            Promise.resolve();
        },
        getPartnerIndicator: function() {
            return this._rpc({
                model: "res.partner",
                method: "get_chat_indicators",
                args: [ [ this.partner_id ] ]
            }).then((result => {
                result["6month_last_sale_data"] && (this.month_last_sale_data = result["6month_last_sale_data"]), 
                result.html_last_sale && (this.html_last_sale = result.html_last_sale);
            }));
        },
        graph_6last_sale: function() {
            let $canvas, context, config, $out = $("<div>");
            return $out.addClass("o_graph_barchart"), this.chart = null, $canvas = $("<canvas/>"), 
            $canvas.height(150), $out.append($canvas), context = $canvas[0].getContext("2d"), 
            config = this._getBarChartConfig(), this.chart = new Chart(context, config), $out;
        },
        _getBarChartConfig: function() {
            var data = [], labels = [];
            let data_param = this.month_last_sale_data;
            return data_param[0].values.forEach((pt => {
                data.push(pt.value), labels.push(pt.label);
            })), {
                type: "bar",
                data: {
                    labels,
                    datasets: [ {
                        data,
                        fill: "start",
                        label: data_param[0].key,
                        backgroundColor: [ "#FFD8E1", "#FFE9D3", "#FFF3D6", "#D3F5F5", "#CDEBFF", "#E6D9FF" ],
                        borderColor: [ "#FF3D67", "#FF9124", "#FFD36C", "#60DCDC", "#4CB7FF", "#A577FF" ]
                    } ]
                },
                options: {
                    legend: {
                        display: !1
                    },
                    scales: {
                        yAxes: [ {
                            display: !1
                        } ]
                    },
                    maintainAspectRatio: !1,
                    tooltips: {
                        intersect: !1,
                        position: "nearest",
                        caretSize: 0,
                        callbacks: {
                            label: (tooltipItem, data) => {
                                var label = data.datasets[tooltipItem.datasetIndex].label || "";
                                return label && (label += ": "), label += this.parent.format_monetary(tooltipItem.yLabel);
                            }
                        }
                    },
                    elements: {
                        line: {
                            tension: 1e-6
                        }
                    }
                }
            };
        }
    });
})), odoo.define("acrux_chat_sale.conversation", (function(require) {
    "use strict";
    require("acrux_chat.conversation").include({
        init: function(parent, options) {
            this._super.apply(this, arguments), this.res_partner_id = this.options.res_partner_id || [ !1, "" ], 
            this.sale_order_id = this.options.sale_order_id || [ !1, "" ], this.partner_sellman_id = this.options.partner_sellman_id || [ !1, "" ];
        },
        _initRender: function() {
            return this._super().then((() => {
                this.$sellman = this.$(".o_acrux_partner_sellman");
            }));
        }
    });
})), odoo.define("acrux_chat_sale.chat_classes", (function(require) {
    "use strict";
    var chat = require("acrux_chat.chat_classes");
    return _.extend(chat, {
        Indicators: require("acrux_chat_sale.indicators"),
        ResPartnerForm: require("acrux_chat_sale.res_partner"),
        SaleOrderForm: require("acrux_chat_sale.sale_order")
    });
})), odoo.define("acrux_chat_sale.acrux_chat", (function(require) {
    "use strict";
    var chat = require("acrux_chat.chat_classes"), AcruxChatAction = require("acrux_chat.acrux_chat").AcruxChatAction;
    AcruxChatAction.include({
        events: _.extend({}, AcruxChatAction.prototype.events, {
            "click li#tab_lastes_sale": "tabLastesSale",
            "click li#tab_partner": "tabPartner",
            "click li#tab_order": "tabOrder"
        }),
        _initRender: function() {
            return this._super().then((() => {
                this.$tab_content_partner = this.$("div#tab_content_partner > div.o_group"), this.$tab_content_order = this.$("div#tab_content_order > div.o_group"), 
                this.$(".o_sidebar_right").find("ul.nav.nav-tabs").find("li > a").click((e => {
                    "#tab_content_partner" != $(e.target).attr("href") && this.product_search.maximize();
                }));
            }));
        },
        getRequiredViews: function() {
            return this._super().then((() => this._rpc({
                model: "ir.model.data",
                method: "get_object_reference",
                args: [ "acrux_chat_sale", "acrux_chat_sale_order_form_view" ]
            }).then((result => {
                this.sale_order_view_id = result[1];
            }))));
        },
        tabPartner: function(event) {
            if (!$(event.currentTarget).find("a").first().hasClass("active") && this.selected_conversation && "current" == this.selected_conversation.status) {
                let partner_id = this.selected_conversation.res_partner_id;
                if (this.res_partner_form && (this.res_partner_form.destroy(), this.res_partner_form = null), 
                !this.res_partner_form) {
                    let options = {
                        context: _.extend({
                            conversation_id: this.selected_conversation.id
                        }, this.action.context),
                        res_partner: partner_id,
                        action_manager: this.action_manager
                    };
                    this.res_partner_form = new chat.ResPartnerForm(this, options), this.res_partner_form.appendTo(this.$tab_content_partner);
                }
            }
        },
        tabOrder: function(event) {
            if (!$(event.currentTarget).find("a").first().hasClass("active") && this.selected_conversation && "current" == this.selected_conversation.status) {
                let sale_order_id = this.selected_conversation.sale_order_id;
                if (this.sale_order_form && (this.sale_order_form.destroy(), this.sale_order_form = null), 
                !this.sale_order_form) {
                    let options = {
                        context: this.action.context,
                        sale_order: sale_order_id,
                        action_manager: this.action_manager,
                        form_name: this.sale_order_view_id
                    };
                    this.sale_order_form = new chat.SaleOrderForm(this, options), this.sale_order_form.appendTo(this.$tab_content_order);
                }
            }
        },
        tabLastesSale: function(event) {
            if (!$(event.currentTarget).find("a").first().hasClass("active") && this.selected_conversation && this.selected_conversation.res_partner_id[0]) {
                this.indicator_widget && this.indicator_widget.destroy();
                let options = {
                    partner_id: this.selected_conversation.res_partner_id[0]
                };
                this.indicator_widget = new chat.Indicators(this, options), this.indicator_widget.appendTo(this.$("div#tab_content_lastes_sale > div.o_group"));
            }
        },
        tabsClear: function() {
            this._super(), this.indicator_widget && (this.indicator_widget.destroy(), this.indicator_widget = null), 
            this.res_partner_form && (this.res_partner_form.destroy(), this.res_partner_form = null), 
            this.sale_order_form && (this.sale_order_form.destroy(), this.sale_order_form = null);
        }
    });
}));