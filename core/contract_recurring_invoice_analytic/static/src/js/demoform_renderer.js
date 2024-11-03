odoo.define('contract_recurring_invoice_analytic.FormRenderer', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var core = require('web.core');
    
    FormRenderer.include({

        setLocalState: function (state) {
            for (const notebook of this.el.querySelectorAll(':scope div.o_notebook')) {
                const name = notebook.dataset.name;
                if (name in state) {
                    const navs = notebook.querySelectorAll(':scope .o_notebook_headers .nav-item');
                    const pages = notebook.querySelectorAll(':scope > .tab-content > .tab-pane');
                    const validTabsAmount = pages.length;
                    if (!validTabsAmount) {
                        continue; // No page defined on the notebook.
                    }
                    let activeIndex = state[name];
                    if (navs[activeIndex] && navs[activeIndex].classList !== "undefined" && navs[activeIndex].classList.contains('o_invisible_modifier')) {
                        activeIndex = [...navs].findIndex(
                            nav => !nav.classList.contains('o_invisible_modifier')
                        );
                    }
                    if (activeIndex <= 0) {
                        continue;
                    }
                    for (let i = 0; i < validTabsAmount; i++) {
                        navs[i].querySelector('.nav-link').classList.toggle('active', activeIndex === i);
                        pages[i].classList.toggle('active', activeIndex === i);
                    }
                    core.bus.trigger('DOM_updated');
                }
            }
        },

    });

    
});