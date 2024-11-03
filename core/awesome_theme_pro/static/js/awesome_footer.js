odoo.define('awesome_theme_pro.footer', function (require) {
    "use strict";

    const patchMixin = require('web.patchMixin');
    const FullScreen = require('awesome_theme_pro.full_screen');
    const config = require('web.config')

    const { Component, hooks } = owl;
    const { useRef, useSubEnv, useState } = hooks;
  
    class AwsomeFooter extends Component {
        constructor() {
            super(...arguments);

            this.state = useState({ 
                isMobile: config.device.isMobile? true : false 
            });

            config.device.bus.on('size_changed', this, this._onDeviceSizeChanged);
        }

        _onDeviceSizeChanged() {
            this.state.isMobile = config.device.isMobile? true : false
        }
    }

    AwsomeFooter.components = {
        FullScreen
    };

    AwsomeFooter.defaultProps = {};
    
    // use the controll pannel props
    AwsomeFooter.props = {};
    AwsomeFooter.template = 'awesome_theme_pro.footer';

    return patchMixin(AwsomeFooter);
});
