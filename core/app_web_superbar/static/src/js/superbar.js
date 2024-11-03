odoo.define('app_web_superbar.Superbar', function (require) {
    //方式一：参考 document 模块的 owl 继承，整体思路改变，做一个新的 SuperBar -> SearchPanel，然后在 abstract_view视图改其 SearchPanel=appSearchPanel
    //方式一测试正常，如下
    // class Superbar extends SearchPanel {
    //     constructor() {
    //         super(...arguments);
    //         console.log('test owl patch');
    //         alert('test owl patch');
    //     }
    // };
    // return Superbar;
    //方式二：patch 原 SearchPanel，参考 mail, activity_renderer.js，暂时不知how

    "use strict";

    const { device } = require("web.config");
    const { Component } = owl;
    const SearchPanel = require("web/static/src/js/views/search_panel.js");
    var SuperbarToggle = require('app_web_superbar.SuperbarToggle');

    class Superbar extends SearchPanel {
        constructor() {
            super(...arguments);
            console.log('test owl patch extension');
        }
        mounted() {
            super.mounted(...arguments);
            if (this.SuperbarToggle)
                this.SuperbarToggle.destroy();
            setTimeout(function () {
                if (!this.SuperbarToggle)
                    this.SuperbarToggle = new SuperbarToggle(this);
                    //要用最后找到的元素，因为有可能主窗体和 pop的 modal窗体都有panel
                    let $node = this.$.find('div.o_cp_top:last');
                    this.SuperbarToggle.prependTo($node);
            }, 100);
        }
        willUnmount() {
            if (this.SuperbarToggle)
                this.SuperbarToggle.destroy();
            return super.willUnmount(...arguments);
        }

        //todo: 点击时，将点箭头与点数据分开处理
        // async _toggleCategory(category, value) {
        //     if (value.childrenIds.length) {
        //         const categoryState = this.state.expanded[category.id];
        //         if (categoryState[value.id] && category.activeValueId === value.id) {
        //             delete categoryState[value.id];
        //         } else {
        //             categoryState[value.id] = true;
        //         }
        //     }
        //     if (category.activeValueId !== value.id) {
        //         this.state.active[category.id] = value.id;
        //         this.model.dispatch("toggleCategoryValue", category.id, value.id);
        //     }
        // };
    };
    Superbar.modelExtension = "Superbar";

    Superbar.defaultProps = Object.assign({}, SearchPanel.defaultProps, {});
    Superbar.props = Object.assign({}, SearchPanel.props, {});
    if (!device.isMobile) {
        Superbar.template = "app.Superbar";
    }
    return Superbar;


});
