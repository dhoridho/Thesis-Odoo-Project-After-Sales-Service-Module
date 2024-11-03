Countdown Widget
================

This module add functionality to add widget directly to char field on web to set clock type widget.

Example:
++++++++++
Add following code to make up proper otherwise you can add direct widget also on field without adding field inside div.

When there will be value for start date it will start timer till end date is passed. once it will get value for end date it will stop timer.

Both start and stop fields should be available on form. if you don't want to show them make them invisible but don't forget to add on view.

Make sure to add default value on field where you apply widget

Pass start field name on 'widget_start_field' and stop field name on 'widget_stop_field'

   <div>
        <button style="pointer-events: none;" class="oe_inline label label-default">
            <field name="field_name" widget="web_time_counter" 
            options="{'widget_start_field': 'start_datetime_field', 'widget_stop_field': 'stop_datetime_field'}" readonly="1"/>
        </button>
    </div>
    <field name="stop_datetime_field"/>
    <field name="start_datetime_field"/>

