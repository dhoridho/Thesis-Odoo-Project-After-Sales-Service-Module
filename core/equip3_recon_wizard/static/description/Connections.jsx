import React from "react";
import { Link } from "react-router-dom";

const Connections = () => {
  return (
    <div className="w-full flex flex-col md:flex-row text-justify gap-y-10 justify-between items-center">
      <div className="w-full space-y-10">
        <div>
          <h1 className="text-3xl md:text-5xl leading-none bg-clip-text text-transparent bg-gradient-to-r from-[#32C2C8] to-[#2E0965] mb-5">
          Why Choose Us Over Hashmicro Native Options:
          </h1>
          <p className="text-xl text-left px-5 text-gray-500">
          Our Quickbooks-inspired interface sets us apart, offering a user-friendly and efficient reconciliation experience unmatched by Hashmicro native options.
          </p>

        </div>
        <div>
        <p className="text-xl text-left px-5 text-gray-500">
          <b>This is the most requested feature by Accountants</b>
          </p>
          <h3 className="font-bold text-2xl mb-2">
            🔹 See all your Accounts in a single view
          </h3>
          <img
            className="mx-5 border-4"
            src="\images\reconciliation\bankingtransaction.png"
            alt="googlesheet odoo connector"
          />
        </div>
        <div>
          <h3 className="font-bold text-2xl mb-2">
            🔹 Select Opening and closing balance and date till you want to reconcile.
          </h3>
          <img
            className="mx-5 border-4 mt-5"
            src="\images\reconciliation\reconcileanaccount.png"
            alt="googlesheet odoo connector"
          />
        </div>
        <div>
          <h3 className="font-bold text-2xl mb-2">
            🔹 Manually checkmark the entries that match.
          </h3>
          <img
            className="mx-5 border-4 mt-5"
            src="\images\reconciliation\saveforlater.png"
            alt="googlesheet odoo connector"
          />
        </div>
        <div>
          <h3 className="font-bold text-2xl mb-2">
            🔹 Click entry and edit if a discrepancy found.
          </h3>
          <img
            className="mx-5 border-4 mt-5"
            src="\images\reconciliation\canceleditsave.png"
            alt="googlesheet odoo connector"
          />
        </div>
        <div>
          <h3 className="font-bold text-2xl mb-2">
            🔹 The difference will become ZERO when transactions match for the period.
          </h3>
          <img
            className="mx-5 border-4 mt-5"
            src="\images\reconciliation\finishnow.png"
            alt="googlesheet odoo connector"
          />
        </div>
        <div>
          <h3 className="font-bold text-2xl mb-2">
            🔹 Simplicity and Control.
          </h3>
          <img
            className="mx-5 border-4 mt-5"
            src="\images\reconciliation\difference.png"
            alt="googlesheet odoo connector"
          />
        </div>
      </div>
    </div>
  );
};

export default Connections;
