odoo.define('equip3_hr_attendance_extend.AttendanceDialog', function (require) {
  "use strict";

  const Dialog = require('web.Dialog');
  const Widget = require('web.Widget');

  const AttendanceDialog = Widget.extend({
      // template: 'attendance_dialog_template',

      events: {
          // 'click .num-btn': '_onNumBtnClick',  // Handle number button clicks
          'click .o_cancel': '_onCancel',      // Handle cancel button click
          // 'click .o_enter': '_onEnter',        // Handle enter button click
      },

      /**
       * @param {Object} parent - The parent object.
       * @param {Object} options - Options for the dialog, including a dynamic function.
       * @param {Function} options.onEnterFunction - A dynamically provided function to execute on "Enter".
       */
      init: function (parent, options) {
          this._super(parent, options);
          this.inputValue = '';  // Initialize the input value
          this.isDialogOpen = false;  // Track dialog state
          this.onEnterFunction = options.onEnterFunction || function () {};  // Fallback to empty function if none is provided
      },

      // Open the dialog
      start: function () {
          const self = this;
          this.dialog = new Dialog(this, {
              title: "Please Input: Attendance ID",
              size: 'small',
              buttons: [
                  { text: 'Cancel', classes: 'btn-secondary o_cancel', close: true },
                  { text: 'Enter', classes: 'btn-primary o_enter', close: false}
              ],
              $content: $('<div>').html(`<div class="attendance-dialog">
                <div class="input-group input-group-attendance">
                    <input type="password" id="attendance_id_pin" class="attendance-input form-control" readonly="readonly"/>
                    <button id="toggle-password" class="btn btn-outline-secondary" type="button">
                        <i id="eye-icon" class="fa fa-eye"></i>
                    </button>
                </div>
                <div class="keypad">
                    <button class="num-btn" data-num="1">1</button>
                    <button class="num-btn" data-num="2">2</button>
                    <button class="num-btn" data-num="3">3</button>
                    <button class="num-btn" data-num="4">4</button>
                    <button class="num-btn" data-num="5">5</button>
                    <button class="num-btn" data-num="6">6</button>
                    <button class="num-btn" data-num="7">7</button>
                    <button class="num-btn" data-num="8">8</button>
                    <button class="num-btn" data-num="9">9</button>
                    <button class="num-btn" data-num="C">C</button>
                    <button class="num-btn" data-num="0">0</button>
                    <button class="num-btn" data-num="x">x</button>
                </div>
            </div>`)
          });

          this.dialog.opened().then(function () {
              self.isDialogOpen = true;
              self.$inputField = self.dialog.$('#attendance_id_pin');
              self.dialog.$modal.find('.modal-header').addClass('header_custom_attendance');
              // Add custom class to the footer if provided
              self.dialog.$modal.find('.modal-footer').addClass('center_footer_attendance');
              // Attach event listener to close dialog on outside click
              $('.modal-dialog').addClass('centered-dialog')
              $('.num-btn').on('click', self._onNumBtnClick.bind(self))
              $('.o_enter').on('click', self._onEnter.bind(self))
              $('#toggle-password').on('click', function(ev){
                ev.stopPropagation();
                const passwordInput = document.querySelector('#attendance_id_pin');
                const eyeIcon = document.querySelector('#eye-icon');
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';  // Show the content
                    eyeIcon.classList.remove('fa-eye');
                    eyeIcon.classList.add('fa-eye-slash');  // Change icon to "eye-slash"
                } else {
                    passwordInput.type = 'password';  // Hide the content
                    eyeIcon.classList.remove('fa-eye-slash');
                    eyeIcon.classList.add('fa-eye');  // Change icon back to "eye"
                }
              })
              $(document).on('click', self._onClickOutside.bind(self));
          });
          this.dialog.open()
      },

      // Handle number button click
      _onNumBtnClick: function (ev) {
          ev.stopPropagation(); 
          const value = $(ev.currentTarget).data('num');
          if (value === 'C') {
              this.inputValue = '';  // Clear input
          } else if (value === 'x') {
              this.inputValue = this.inputValue.slice(0, -1);  // Remove last digit
          } else {
              this.inputValue += value;  // Append number
          }

          // Update the input field
          this.$inputField.val(this.inputValue);
      },

      // Handle Enter button click
      _onEnter: function () {
          const enteredValue = this.inputValue;

          // Example: Validate the entered ID
          if (enteredValue.length === 0) {
              alert("Please enter an ID before proceeding!");
          } else {
              // Dynamically call the provided function with the entered value
              if (typeof this.onEnterFunction === 'function') {
                  this.onEnterFunction(enteredValue);
              } else {
                  console.error("No valid function passed to AttendanceDialog for handling the Enter event.");
              }
          }

          // Optionally close the dialog after submission
          this._closeDialog();
      },

      // Handle cancel button click
      _onCancel: function () {
          this._closeDialog();
      },

      // Close the dialog and clean up
      _closeDialog: function () {
          if (this.isDialogOpen) {
              this.isDialogOpen = false;
              this.dialog.close();
              $(document).off('click', this._onClickOutside);  // Remove the outside click listener
          }
      },

      // Detect clicks outside the dialog and close it
      _onClickOutside: function (ev) {
          const dialogContent = this.dialog.$modal.find('.modal-dialog');
          const clickedOutside = !dialogContent.is(ev.target) && dialogContent.has(ev.target).length === 0;

          if (clickedOutside) {
              this._closeDialog();
          }
      }
  });

  return AttendanceDialog;
});
