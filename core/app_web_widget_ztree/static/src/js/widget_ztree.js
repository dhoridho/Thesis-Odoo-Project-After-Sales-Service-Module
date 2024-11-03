odoo.define('app_web_widget_ztree.zTree', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;
    var fieldRegistry = require('web.field_registry');
    var AbstractField = require('web.AbstractField');
    var relational_fields = require('web.relational_fields');
    var FieldMany2One = relational_fields.FieldMany2One;
    //zTree 最多显示的记录数，在没limit参数时生效
    var ztree_Max = 1000;

    // 生成一个zTree
    var zTree = Widget.extend({
        className: 'ztree',
        template: 'App.zTree',
        init: function (setting, data) {
            this._super.apply(this, arguments);
            this.setting = {
                view: {
                    selectedMulti: true,
                    fontCss: function getFont(treeId, node) {
                        return node.font ? node.font : {};
                    },
                    nameIsHTML: true,
                    showIcon: false,
                    txtSelectedEnable: true,
                },
                data: {
                    key: {
                        title: "title"
                    },
                    simpleData: {
                        enable: true,
                    }
                }
            };
            if (setting)
                $.extend(this.setting, setting);

            //如果有定义zNodes，则直接按 zNodes数据展现，否则 rpc 取

            if (data.zNodes && data.zNodes.length)
                this.zNodes = data.zNodes;
            this.ztree_field = data.ztree_field;
            this.ztree_model = data.ztree_model;
            this.ztree_parent_key = data.ztree_parent_key;
            //todo: root_id，这个是节点的根id，用 parent_left < x < parent_right 实现，在 domain 增加值
            this.ztree_root_id = data.ztree_root_id;
            this.ztree_domain = data.ztree_domain;
            this.ztree_context = data.ztree_context ? data.ztree_context : session.user_context;
            this.order = data.order;
            this.ztree_selected_id = Number(data.ztree_selected_id);
            this.ztree_selected_vals = [];
            this.ztree_with_sub_node = data.ztree_with_sub_node;
            this.ztree_index = data.ztree_index;
            this.ztree_add_show_all = data.ztree_add_show_all;
            //默认2级
            this.ztree_expend_level = data.ztree_expend_level ? data.ztree_expend_level : 2;
            this.ztree_name_field = data.ztree_name_field;
            this.limit = data.limit > 0 ? data.limit : ztree_Max;
            this.ztree_id = 'ztree-' + this.guid();
            this.ztree_type = data.ztree_type;

        },
        willStart: function () {
            //数据初始化
            var self = this;
            var def;
            //不可用 ._rpc
            if (!self.zNodes || self.zNodes.length <= 0) {
                def = rpc.query({
                    model: self.ztree_model,
                    method: 'search_ztree',
                    kwargs: {
                        domain: self.ztree_domain,
                        context: self.ztree_context,
                        parent_key: self.ztree_parent_key,
                        root_id: self.ztree_root_id,
                        expend_level: self.ztree_expend_level,
                        name_field: self.ztree_name_field,
                        order: self.order,
                        limit: parseInt(self.limit? self.limit : ztree_Max),
                        //如果 type='chart'，要按 selected_id 得到 root_id 遍历
                        type: self.ztree_type,
                        selected_id: self.ztree_selected_id,
                    },
                }).then(function (result) {
                    var showall = [];
                    if (result.length > 0) {
                        self.zNodes = showall.concat(result);
                    }
                });
            }
            return $.when(this._super.apply(this, arguments), def);
        },
        start: function () {
            var self = this;
            this._super.apply(this, arguments);
            if (!self.$zTree) {
                self.$zTree = $.fn.zTree.init(self.$el, self.setting, self.zNodes);
                if (self.ztree_selected_id != null && self.ztree_selected_id > 0) {
                    var node = self.$zTree.getNodeByParam('id', self.ztree_selected_id, null);
                    self.$zTree.selectNode(node);
                }
            }
        },
        destroy: function () {
            if (this.$zTree) {
                this.$el.remove();
                this.$zTree = undefined;
            }
            this._super();
        },
        guid: function () {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        },
        getChildNodes: function getChildNodes(treeNode) {
            var childNodes = this.$zTree.transformToArray(treeNode);
            var nodes = new Array();
            var i;
            for (i = 0; i < childNodes.length; i++) {
                nodes[i] = childNodes[i].id;
            }

            return nodes.join(",");
        }
    });

    var FieldZTree = FieldMany2One.extend({
        supportedFieldTypes: ['many2one'],
        //todo: many2many
        template: 'App.FieldZtree',
        SEARCH_MORE_LIMIT: 1000,

        init: function () {
            this._super.apply(this, arguments);
            this.limit = this.attrs.limit ? this.attrs.limit : 1000;
            this.nodeOptions.quick_create = false;
            this.nodeOptions.no_quick_create = true;
            this.ztree_parent_key = this.nodeOptions.ztree_parent_key;
            this.ztree_root_id = this.nodeOptions.ztree_root_id;
            this.ztree_name_field = this.nodeOptions.ztree_name_field;
            this.order = this.nodeOptions.order;
            this.ztree_expend_level = this.nodeOptions.ztree_expend_level;
        },
        start: function () {
            this._super.apply(this, arguments);
            var self = this;
            //点击外部关闭ztree
            $(document).delegate('body', 'click', function (ev) {
                var $parent = $(ev.target).parents('.o_input_dropdown')
                if (!$parent.length && self.many2one) {
                    self._close();
                } else if (!$parent.find('.ztree').length) {
                    self._close();
                }
            });
        },
        _bindAutoComplete: function () {
            var self = this;
            this._super.apply(this, arguments);
            this.$input.autocomplete({
                source: function (req) {
                    if (!self.many2one)
                        self.buildTreeView(req.term);
                },
                focus: function (event, ui) {
                    event.preventDefault(); // don't automatically select values on focus
                },
                close: function (event, ui) {
                    if (event.which === $.ui.keyCode.ESCAPE) {
                        event.stopPropagation();
                    }
                    console.log('ui close');
                },
                autoFocus: true,
                html: true,
                minLength: 0,
                delay: this.AUTOCOMPLETE_DELAY,
            });

            this.$input.autocomplete("option", "position", {my: "left top", at: "left bottom"});
        },
        _selectNode: function (event, item) {
            var self = this;
            self.$input.autocomplete("close");
            // console.log(arguments);
            event.stopImmediatePropagation();
            event.preventDefault();
            event.stopPropagation();
            self.floating = false;
            if (item.id) {
                self.reinitialize({id: item.id, display_name: item.name});
            } else if (item.action) {
                item.action();
            }
            self._close();
            return false;
        },
        _onInputClick: function (ev) {
            this._super.apply(this, arguments);
            var $parent = $(ev.target).parents('.o_input_dropdown')
            if ($parent.find('.ztree').length && this.many2one) {
                this._close();
            }
        },
        _onInputKeyup: function (ev) {
            this._super.apply(this, arguments);
            if (event.which === $.ui.keyCode.ESCAPE) {
                event.stopPropagation();
                this._close();
            } else
                this.buildTreeView(ev.target.value);
        },
        _onInputFocusout: function () {
            ;
        },
        _close: function () {
            var self = this;
            if (self.many2one)
                self.many2one.destroy();
            try {
                self.many2one.$el.remove();
            } catch (err) {
                ;
            }
            self.many2one = undefined;
        },
        _search: function (search_val) {
            var self = this;

            var def = new Promise(function (resolve, reject) {
                var context = self.record.getContext(self.recordParams);
                var domain = self.record.getDomain(self.recordParams);

                // Add the additionalContext
                _.extend(context, self.additionalContext);

                var blacklisted_ids = self._getSearchBlacklist();
                if (blacklisted_ids.length > 0) {
                    domain.push(['id', 'not in', blacklisted_ids]);
                }
                if (search_val && search_val != "") {
                    domain.push(['name', 'ilike', search_val]);
                }

                var parent_key = self.ztree_parent_key;
                var root_id = self.ztree_root_id;
                var expend_level = self.ztree_expend_level;
                var name_field = self.ztree_name_field;
                self._rpc({
                    model: self.field.relation,
                    method: "search_ztree",
                    kwargs: {
                        domain: domain,
                        context: context,
                        parent_key: parent_key,
                        root_id: root_id,
                        expend_level: expend_level,
                        name_field: name_field,
                        limit: parseInt(self.limit + 1),
                        order: self.order,
                    }
                })
                    .then(function (result) {
                        var values = result;
                        // search more... if more results than limit
                        if (values.length > self.limit) {
                            values = self._manageSearchMore(values, search_val, domain, context);
                        }
                        var create_enabled = self.can_create && !self.nodeOptions.no_create;
                        // quick create，默认关闭
                        var raw_result = _.map(result, function (x) { return x[1]; });

                        if (create_enabled && !self.nodeOptions.no_quick_create &&
                            search_val.length > 0 && !_.contains(raw_result, search_val)) {
                            values.push({
                                id: null,
                                name: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                                    $('<span />').text(search_val).html()),
                                font: {'color': '#00A09D', 'font-weight': 'bold'},
                                label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                                    $('<span />').text(search_val).html()),
                                action: self._quickCreate.bind(self, search_val),
                                classname: 'o_m2o_dropdown_option'
                            });
                        }
                        // create and edit ...
                        if (create_enabled && !self.nodeOptions.no_create_edit) {
                            var createAndEditAction = function () {
                                // Clear the value in case the user clicks on discard
                                self.$('input').val('');
                                return self._searchCreatePopup("form", false, self._createContext(search_val));
                            };
                            values.push({
                                id: null,
                                name: _t("Create and Edit..."),
                                font: {'color': '#00A09D', 'font-weight': 'bold'},
                                label: _t("Create and Edit..."),
                                action: createAndEditAction,
                                classname: 'o_m2o_dropdown_option',
                            });
                        } else if (values.length === 0) {
                            values.push({
                                id: null,
                                name: _t("No results to show..."),
                                font: {'color': '#00A09D', 'font-weight': 'bold'},
                                label: _t("No results to show..."),
                            });
                        }
                        resolve(values);
                    });
            });
            this.orderer.add(def);
            return def;
        },
        buildTreeView: function (search_val) {
            var self = this;
            var domain = self.record.getDomain(self.recordParams);

            var blacklisted_ids = self._getSearchBlacklist();
            if (blacklisted_ids.length > 0) {
                domain.push(['id', 'not in', blacklisted_ids]);
            }
            if (self.many2one) {
                self.many2one.destroy();
                self.many2one = undefined;
            }
            var setting = {
                callback: {
                    onClick: function (event, treeId, treeNode, clickFlag) {
                        self._selectNode(event, treeNode);
                    }
                }
            };
            self._search(search_val).then(function (result) {
                //todo: 不能默认让node selected，会出现quick_create 混乱
                if (self.value && self.value.data.id && self.value.data.id > 0)
                    var ztree_selected_id = self.value.data.id;
                self.many2one = new zTree(setting, {
                    zNodes: result,
                    ztree_domain: domain,
                    ztree_field: self.field.name,
                    ztree_model: self.field.relation,
                    ztree_parent_key: self.ztree_parent_key,
                    ztree_root_id: self.ztree_root_id,
                    ztree_expend_level: self.ztree_expend_level,
                    ztree_name_field: self.ztree_name_field,
                    ztree_selected_id: ztree_selected_id,
                });
                self.many2one.appendTo(self.$input.parent());
                // self.$(".ztree").replaceWith(self.many2one);
                self.$input.css('height', 'auto');
            });
        },
        // public

        // private
    });

    var FieldZTreeChart = AbstractField.extend({
        noLabel: true,
        supportedFieldTypes: ['one2many'],
        //todo: many2many
        template: 'App.FieldZtreeChart',
        SEARCH_MORE_LIMIT: 1000,

        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            //初始参数，parent, name, record, options
            this.no_title = false;
            this.limit = this.attrs.limit ? this.attrs.limit : 1000;
            this.ztree_parent_key = this.nodeOptions.ztree_parent_key;
            this.ztree_root_id = this.nodeOptions.ztree_root_id;
            this.ztree_name_field = this.nodeOptions.ztree_name_field;
            this.order = this.nodeOptions.order;
            this.ztree_expend_level = this.nodeOptions.ztree_expend_level || 5;
        },
        _selectNode: function (event, item) {
            var self = this;
            var action = {};
            // console.log(arguments);
            event.stopImmediatePropagation();
            event.preventDefault();
            event.stopPropagation();
            var context = _.extend({}, self.context);
            var clear = parseInt(item.pId) > 0 ? false : true;
            if (item.id && item.id != self.res_id) {
                action = {
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    target: 'current',
                    res_model: this.model,
                    res_id: item.id,
                    context: context,
                };
                return this.do_action(action, {clear_breadcrumbs: clear,});
            }
        },
        _renderEdit: function () {
            var self = this;
            //此处不可 domain，因为可以会造成树不全
            // var domain = self.record.getDomain(self.recordParams);
            var domain = [];
            // 用callback，不用url，更灵活
            var setting = {
                callback: {
                    onClick: function (event, treeId, treeNode) {
                        self._selectNode(event, treeNode);
                    }
                }
            };

            var $ztree = new zTree(setting, {
                    ztree_field: self.field.name,
                    ztree_model: self.field.relation,
                    ztree_domain: domain,
                    ztree_parent_key: self.ztree_parent_key,
                    ztree_root_id: self.ztree_root_id,
                    ztree_expend_level: self.ztree_expend_level,
                    ztree_name_field: self.ztree_name_field,
                    ztree_selected_id: self.record.res_id,
                    ztree_type: 'chart',
                }
            );
            $ztree.appendTo(this.$el.find('.ztree_chart'));
        },
        _renderReadonly: function () {
            this._renderEdit();
        },
    });

    fieldRegistry.add('ztree_select', FieldZTree);
    fieldRegistry.add('ztree_chart', FieldZTreeChart);

    return {
        zTree: zTree,
        FieldZTree: FieldZTree,
        FieldZTreeChart: FieldZTreeChart,
    };
});
